"""Toga-backed :class:`dbs_annotator.gui.Paths`.

Wraps ``toga.App.paths`` (platformdirs-equivalent under the hood). On
mobile this resolves to the app sandbox (``Documents/`` / internal
storage) so data survives app updates.
"""

from __future__ import annotations

from pathlib import Path


class TogaPaths:
    def __init__(self, app) -> None:  # type: ignore[no-untyped-def]
        self._app = app

    def user_data_dir(self) -> Path:
        path = Path(str(self._app.paths.data))
        path.mkdir(parents=True, exist_ok=True)
        return path

    def user_log_dir(self) -> Path:
        try:
            base = Path(str(self._app.paths.logs))
        except AttributeError:
            base = self.user_data_dir() / "logs"
        base.mkdir(parents=True, exist_ok=True)
        return base

    def generic_data_base(self) -> Path | None:
        return self.user_data_dir().parent
