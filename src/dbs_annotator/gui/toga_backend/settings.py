"""Toga-backed :class:`dbs_annotator.gui.SettingsProtocol` + ``UpdaterStore``.

Persistence is a small JSON file under the Toga ``app.paths.config``
directory. On iOS this lands in the app's Documents container; on
Android in internal app storage. Writes are best-effort -- we never
raise from a settings write so transient file-system errors do not take
the app down.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SETTINGS_FILENAME = "settings.json"
_UPDATER_FILENAME = "updater_state.json"
_LAST_CHECK_KEY = "last_check_iso"


def _load(path: Path) -> dict[str, Any]:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.info("Could not read %s; starting fresh", path)
    return {}


def _save(path: Path, data: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        logger.info("Could not write %s", path)


class TogaSettings:
    def __init__(self, config_dir: Path) -> None:
        self._path = config_dir / _SETTINGS_FILENAME
        self._cache: dict[str, Any] | None = None

    def _state(self) -> dict[str, Any]:
        if self._cache is None:
            self._cache = _load(self._path)
        return self._cache

    def get(self, key: str, default: Any = None) -> Any:
        return self._state().get(key, default)

    def set(self, key: str, value: Any) -> None:
        state = self._state()
        state[key] = value
        _save(self._path, state)


class TogaUpdaterStore:
    def __init__(self, config_dir: Path) -> None:
        self._path = config_dir / _UPDATER_FILENAME

    def last_check(self) -> datetime | None:
        data = _load(self._path)
        raw = data.get(_LAST_CHECK_KEY)
        if not isinstance(raw, str) or not raw:
            return None
        try:
            dt = datetime.fromisoformat(raw)
        except ValueError:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt

    def record_check(self, when: datetime) -> None:
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        data = _load(self._path)
        data[_LAST_CHECK_KEY] = when.isoformat()
        _save(self._path, data)

    def cooldown_elapsed(self, cooldown: timedelta, now: datetime) -> bool:
        last = self.last_check()
        if last is None:
            return True
        return (now - last) >= cooldown
