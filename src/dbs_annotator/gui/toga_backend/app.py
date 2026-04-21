"""Toga ``App`` entry point for the migrated build.

Thin shell that boots the Toga backend, installs the
:mod:`dbs_annotator.gui` abstractions, and displays the wizard. The
heavy business logic lives in ``gui.toga_backend.wizard_flow`` and the
view classes under ``gui.toga_backend.views``.
"""

from __future__ import annotations

import asyncio
import logging

import toga
from toga.style.pack import COLUMN, Pack

from ... import __version__
from ...utils.updater import UpdateChecker
from .bootstrap import install as install_toga_backend
from .theme import LIGHT
from .views.wizard_window import WizardWindow

logger = logging.getLogger(__name__)


class DBSAnnotatorApp(toga.App):
    def startup(self) -> None:
        install_toga_backend(self)

        _p = LIGHT
        self.status_label = toga.Label("", style=Pack(margin=6, color=_p.subtle))

        self.wizard = WizardWindow(self)

        layout = toga.Box(
            style=Pack(direction=COLUMN, flex=1, background_color=_p.surface)
        )
        layout.add(self.wizard.content)
        layout.add(self.status_label)

        main = toga.MainWindow(title=f"DBS Annotator v{__version__}", size=(1280, 900))
        main.content = layout
        main.show()
        self.main_window = main

        self.on_running = self._check_updates  # ty: ignore[invalid-assignment]

    async def _check_updates(self, *_: object, **__: object) -> None:
        try:
            await asyncio.sleep(1.5)
            checker = UpdateChecker()
            checker.check_async()
        except Exception:  # pragma: no cover
            logger.exception("Update check failed")


def main() -> DBSAnnotatorApp:
    from ...config import FS_APP_NAME, FS_ORG_NAME

    return DBSAnnotatorApp(
        formal_name="DBSAnnotator",
        app_id=f"ch.wysscenter.{FS_APP_NAME.lower()}",
        app_name="dbs_annotator",
        author=FS_ORG_NAME,
    )
