"""Qt-backed :class:`dbs_annotator.gui.Paths` implementation.

Uses :class:`PySide6.QtCore.QStandardPaths` to resolve platform-appropriate
directories. Identical behaviour to the pre-refactor implementation that
lived inline in :mod:`dbs_annotator.utils.user_data` and
:mod:`dbs_annotator.logging_config`.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QStandardPaths


class QtPaths:
    def user_data_dir(self) -> Path:
        location = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppLocalDataLocation
        )
        base = Path(location) if location else Path.home() / ".dbs-annotator"
        base.mkdir(parents=True, exist_ok=True)
        return base

    def user_log_dir(self) -> Path:
        log_dir = self.user_data_dir() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

    def generic_data_base(self) -> Path | None:
        try:
            base = QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.GenericDataLocation
            )
        except Exception:
            return None
        return Path(base) if base else None
