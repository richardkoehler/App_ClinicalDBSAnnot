"""Install the Toga backend into :mod:`dbs_annotator.gui`.

Call this *after* ``toga.App`` has been constructed (so ``app.paths`` is
resolvable) but *before* any of the app modules call ``gui.get_*``.
"""

from __future__ import annotations

from pathlib import Path

from ..clock import SystemClock
from ..interfaces import register_backend
from .background import TogaBackgroundRunner
from .paths import TogaPaths
from .settings import TogaSettings, TogaUpdaterStore

_installed = False


def install(app) -> None:  # type: ignore[no-untyped-def]
    """Register the Toga implementations. Idempotent."""
    global _installed
    if _installed:
        return
    paths = TogaPaths(app)
    config_dir = Path(str(app.paths.config))
    config_dir.mkdir(parents=True, exist_ok=True)
    register_backend(
        paths=paths,
        settings=TogaSettings(config_dir),
        background_runner=TogaBackgroundRunner(),
        clock=SystemClock(),
        updater_store=TogaUpdaterStore(config_dir),
    )
    _installed = True
