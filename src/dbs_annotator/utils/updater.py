"""Check GitHub Releases for newer versions of the app.

Design goals:

* Silent on failure -- a missing network connection, a GitHub outage, or a
  rate limit must never block startup or show an error dialog to the user.
* At most one check per cooldown window (default 24 h) so repeated launches
  do not spam the GitHub API. The last-check timestamp is persisted via
  :class:`UpdaterStore` (``QSettings`` under the Qt backend; a JSON file
  under the Toga backend) so it survives between sessions but never leaks
  PII.
* The HTTP fetch runs on a worker thread via the GUI backend's
  :class:`BackgroundRunner` (``QThreadPool`` today, ``asyncio.to_thread``
  after the migration); the main-thread slot is only invoked if a strictly
  newer version is found.
* The user can always trigger a check from a menu / button with
  ``force=True``.

The release repository is hardcoded to the canonical upstream; change
:data:`DEFAULT_RELEASES_REPO` if the project moves.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from packaging.version import InvalidVersion, Version

from .. import __version__
from ..gui import get_background_runner, get_clock, get_updater_store

try:  # PySide6 is optional for Toga-only / mobile builds.
    from PySide6.QtCore import QObject, Signal  # type: ignore[import-not-found]

    _HAS_QT = True
except ImportError:  # pragma: no cover -- exercised by mobile builds
    _HAS_QT = False

    class _Signal:
        """Lightweight stand-in for ``PySide6.QtCore.Signal``.

        Supports ``connect``/``disconnect``/``emit`` so existing slot-wire
        code keeps working when Qt is absent.
        """

        def __init__(self) -> None:
            self._slots: list[Callable[..., None]] = []

        def connect(self, slot: Callable[..., None]) -> None:
            self._slots.append(slot)

        def disconnect(self, slot: Callable[..., None] | None = None) -> None:
            if slot is None:
                self._slots.clear()
                return
            try:
                self._slots.remove(slot)
            except ValueError:
                pass

        def emit(self, *args: object) -> None:
            for slot in list(self._slots):
                try:
                    slot(*args)
                except Exception:  # noqa: BLE001
                    logging.getLogger(__name__).exception("Updater signal slot raised")

    class _SignalDescriptor:
        """Class-body descriptor so every QObject instance gets its own signal."""

        def __init__(self, *_: object) -> None:
            self._attr = f"_signal_{id(self)}"

        def __get__(self, obj: object, _owner: type | None = None) -> _Signal:
            if obj is None:
                # Accessed on the class; return a dummy throwaway signal so
                # typed consumers still see a ``_Signal``.
                return _Signal()
            cache = obj.__dict__.setdefault(self._attr, _Signal())
            return cache

    class QObject:  # type: ignore[no-redef]
        def __init__(self, parent: object | None = None) -> None:
            self._parent = parent

    def Signal(*args: object) -> _Signal:  # type: ignore[no-redef]  # noqa: N802 -- mimics PySide6 Signal factory
        from typing import cast

        return cast("_Signal", _SignalDescriptor(*args))


logger = logging.getLogger(__name__)

#: Owner/repo pair on GitHub whose releases advertise new builds.
DEFAULT_RELEASES_REPO = "Brain-Modulation-Lab/App_ClinicalDBSAnnot"

DEFAULT_COOLDOWN = timedelta(hours=24)
DEFAULT_TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class ReleaseInfo:
    """Metadata for a GitHub release that is newer than the running app."""

    version: str
    tag_name: str
    html_url: str
    published_at: str
    body: str


def _parse_version(tag: str) -> Version | None:
    """Parse a release tag or version string with ``packaging.version``.

    Returns ``None`` if the tag does not look like a PEP 440-compatible
    version -- most commonly a lightweight tag used for infrastructure. Such
    tags are ignored for update-check purposes.
    """
    candidate = tag.lstrip("vV").strip()
    try:
        return Version(candidate)
    except InvalidVersion:
        return None


def _fetch_latest_release(
    repo: str, current_version: str, timeout: float
) -> ReleaseInfo | None:
    """Blocking GitHub fetch; runs on a worker thread."""
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"DBSAnnotator/{current_version}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.info("Updater fetch failed: %s", exc)
        raise

    tag = str(payload.get("tag_name", ""))
    if not tag:
        return None

    remote = _parse_version(tag)
    local = _parse_version(current_version)
    if remote is None or local is None:
        logger.debug(
            "Skipping update comparison for tag=%r current=%r",
            tag,
            current_version,
        )
        return None
    if payload.get("prerelease"):
        return None
    if remote <= local:
        return None

    return ReleaseInfo(
        version=str(remote),
        tag_name=tag,
        html_url=str(payload.get("html_url", "")),
        published_at=str(payload.get("published_at", "")),
        body=str(payload.get("body", "")),
    )


class UpdateChecker(QObject):  # ty: ignore[unsupported-base]
    """Orchestrates background update checks with a configurable cooldown.

    Create one of these on the main thread (typically owned by the main
    window) and call :meth:`check_async`. A ``check_async(force=True)`` call
    bypasses the cooldown -- wire it to a "Check for updates" menu action.
    """

    update_available = Signal(object)
    up_to_date = Signal()
    failed = Signal(str)

    def __init__(
        self,
        repo: str = DEFAULT_RELEASES_REPO,
        current_version: str | None = None,
        cooldown: timedelta = DEFAULT_COOLDOWN,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._repo = repo
        self._current_version = current_version or __version__
        self._cooldown = cooldown
        self._timeout = timeout
        self._store = get_updater_store()
        self._runner = get_background_runner()
        self._clock = get_clock()

    def check_async(
        self,
        *,
        force: bool = False,
        now: Callable[[], datetime] | None = None,
    ) -> bool:
        """Schedule a background check.

        Args:
            force: If True, bypass the cooldown.
            now: Injectable clock, only for tests.

        Returns:
            True if a check was scheduled; False if the cooldown suppressed
            it.
        """
        current_time = (now or self._clock.now)()
        if not force and not self._store.cooldown_elapsed(self._cooldown, current_time):
            return False

        repo = self._repo
        current_version = self._current_version
        timeout = self._timeout

        self._runner.submit(
            lambda: _fetch_latest_release(repo, current_version, timeout),
            on_success=self._handle_success,
            on_error=self._handle_error,
        )
        return True

    def _handle_success(self, latest: ReleaseInfo | None) -> None:
        self._store.record_check(self._clock.now())
        if latest is None:
            self.up_to_date.emit()
        else:
            self.update_available.emit(latest)

    def _handle_error(self, exc: BaseException) -> None:
        # Intentionally do NOT record a check time on hard failures so the
        # next launch retries instead of waiting out the cooldown.
        self.failed.emit(str(exc))
