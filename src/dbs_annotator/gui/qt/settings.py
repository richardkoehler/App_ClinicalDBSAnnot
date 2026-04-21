"""Qt-backed :class:`dbs_annotator.gui.SettingsProtocol` and
:class:`UpdaterStore` implementations.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from PySide6.QtCore import QSettings

_LAST_CHECK_KEY = "updater/last_check_iso"


class QtSettings:
    def __init__(self) -> None:
        self._settings = QSettings()

    def get(self, key: str, default: Any = None) -> Any:
        val = self._settings.value(key, default)
        return val if val is not None else default

    def set(self, key: str, value: Any) -> None:
        self._settings.setValue(key, value)


class QtUpdaterStore:
    def __init__(self) -> None:
        self._settings = QSettings()

    def last_check(self) -> datetime | None:
        raw = self._settings.value(_LAST_CHECK_KEY, "")
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
        self._settings.setValue(_LAST_CHECK_KEY, when.isoformat())

    def cooldown_elapsed(self, cooldown: timedelta, now: datetime) -> bool:
        last = self.last_check()
        if last is None:
            return True
        return (now - last) >= cooldown
