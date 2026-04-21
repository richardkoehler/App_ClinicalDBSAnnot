"""One-shot registration of the Qt backend into :mod:`dbs_annotator.gui`."""

from __future__ import annotations

from ..interfaces import register_backend
from .background import QtBackgroundRunner
from .clock import SystemClock
from .paths import QtPaths
from .settings import QtSettings, QtUpdaterStore

_installed = False


def install() -> None:
    """Register the Qt implementations. Idempotent."""
    global _installed
    if _installed:
        return
    register_backend(
        paths=QtPaths(),
        settings=QtSettings(),
        background_runner=QtBackgroundRunner(),
        clock=SystemClock(),
        updater_store=QtUpdaterStore(),
    )
    _installed = True
