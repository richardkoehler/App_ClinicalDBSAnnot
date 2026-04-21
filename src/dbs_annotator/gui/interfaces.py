"""Backend-neutral interfaces used by the rest of the app.

The active backend is selected at import time by whichever concrete
module calls :func:`register_backend` first. Today this is
``gui.qt.bootstrap`` (invoked from ``dbs_annotator.__main__``); after
Phase 2 it will be ``gui.toga_backend.bootstrap``.

All public names here are either ``typing.Protocol`` descriptions
(interfaces) or registry accessors (``get_*``). They are **not**
dependent on PySide6 or Toga.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

# ---------- Paths ----------


@runtime_checkable
class Paths(Protocol):
    """Platform-appropriate writable locations for user data, cache, logs."""

    def user_data_dir(self) -> Path: ...

    def user_log_dir(self) -> Path: ...

    def generic_data_base(self) -> Path | None:
        """Parent of per-app data (for legacy-path probing). ``None`` if unknown."""


# ---------- Settings ----------


@runtime_checkable
class SettingsProtocol(Protocol):
    """Small key/value store that survives upgrades (QSettings/JSON/plist)."""

    def get(self, key: str, default: Any = None) -> Any: ...

    def set(self, key: str, value: Any) -> None: ...


# Alias kept for callers that prefer the shorter name.
Settings = SettingsProtocol


# ---------- Background work ----------


@runtime_checkable
class BackgroundRunner(Protocol):
    """Run a blocking callable off the UI thread.

    The returned callable is a "cancel" handle; best-effort on all
    backends (Qt's QRunnable cannot truly be cancelled, asyncio tasks
    can).
    """

    def submit(
        self,
        func: Callable[..., Any],
        *,
        on_success: Callable[[Any], None] | None = None,
        on_error: Callable[[BaseException], None] | None = None,
    ) -> Callable[[], None]: ...


# ---------- Clock ----------


@runtime_checkable
class Clock(Protocol):
    """Injectable clock so tests can control time deterministically."""

    def now(self) -> datetime: ...


# ---------- Updater persistence ----------


@runtime_checkable
class UpdaterStore(Protocol):
    """Persistence used by the update checker (``QSettings`` today)."""

    def last_check(self) -> datetime | None: ...

    def record_check(self, when: datetime) -> None: ...

    def cooldown_elapsed(self, cooldown: timedelta, now: datetime) -> bool: ...


# ---------- Registry ----------

_registry: dict[str, Any] = {}


def register_backend(
    *,
    paths: Paths | None = None,
    settings: SettingsProtocol | None = None,
    background_runner: BackgroundRunner | None = None,
    clock: Clock | None = None,
    updater_store: UpdaterStore | None = None,
) -> None:
    """Install concrete implementations. Must be called once at app start.

    Any argument left as ``None`` keeps whatever was previously
    registered (so the Qt backend can be set once and tests can then
    override individual pieces).
    """
    if paths is not None:
        _registry["paths"] = paths
    if settings is not None:
        _registry["settings"] = settings
    if background_runner is not None:
        _registry["background_runner"] = background_runner
    if clock is not None:
        _registry["clock"] = clock
    if updater_store is not None:
        _registry["updater_store"] = updater_store


def _require(key: str) -> Any:
    try:
        return _registry[key]
    except KeyError as exc:
        raise RuntimeError(
            f"GUI backend not initialised: missing {key}. "
            "Call dbs_annotator.gui.qt.bootstrap.install() at app start."
        ) from exc


def get_paths() -> Paths:
    return _require("paths")


def get_settings() -> SettingsProtocol:
    return _require("settings")


def get_background_runner() -> BackgroundRunner:
    return _require("background_runner")


def get_clock() -> Clock:
    return _require("clock")


def get_updater_store() -> UpdaterStore:
    return _require("updater_store")
