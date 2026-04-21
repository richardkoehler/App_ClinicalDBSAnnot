"""Async release-check (drops QThreadPool/QRunnable in favour of asyncio).

This is the Toga equivalent of ``src/dbs_annotator/utils/updater.py``. It
demonstrates that:

* The HTTP fetch runs on a worker thread via ``asyncio.to_thread``.
* Persistence uses ``toga.App.paths.data`` (platformdirs-equivalent) rather
  than ``QSettings``.

No Qt import.
"""

from __future__ import annotations

import asyncio
import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_REPO = "Brain-Modulation-Lab/App_ClinicalDBSAnnot"
DEFAULT_COOLDOWN = timedelta(hours=24)
DEFAULT_TIMEOUT = 10.0
LAST_CHECK_KEY = "updater_last_check_iso"


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    tag_name: str
    html_url: str
    published_at: str
    body: str


def _blocking_fetch(repo: str, timeout: float) -> dict | None:
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "DBSAnnotator-PoC/0.1",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = resp.read().decode("utf-8")
        return json.loads(payload)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.info("Updater fetch failed (silent): %s", exc)
        return None


def _load_state(state_path: Path) -> dict:
    try:
        if state_path.exists():
            return json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def _save_state(state_path: Path, state: dict) -> None:
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state), encoding="utf-8")
    except OSError:
        pass


async def check_async(
    state_path: Path,
    *,
    repo: str = DEFAULT_REPO,
    cooldown: timedelta = DEFAULT_COOLDOWN,
    timeout: float = DEFAULT_TIMEOUT,
    force: bool = False,
) -> ReleaseInfo | None:
    """Run a single release check, respecting the cooldown window."""
    state = _load_state(state_path)
    if not force:
        last_iso = state.get(LAST_CHECK_KEY)
        if last_iso:
            try:
                last = datetime.fromisoformat(last_iso)
                if datetime.now(UTC) - last < cooldown:
                    return None
            except ValueError:
                pass

    payload = await asyncio.to_thread(_blocking_fetch, repo, timeout)
    state[LAST_CHECK_KEY] = datetime.now(UTC).isoformat()
    _save_state(state_path, state)

    if not payload:
        return None
    return ReleaseInfo(
        version=str(payload.get("tag_name", "")).lstrip("v"),
        tag_name=str(payload.get("tag_name", "")),
        html_url=str(payload.get("html_url", "")),
        published_at=str(payload.get("published_at", "")),
        body=str(payload.get("body", "")),
    )
