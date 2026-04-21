"""Cross-platform open / share helpers for the Toga build.

Replaces the mix of ``os.startfile``, ``subprocess.Popen(['xdg-open', ...])``
and ``QDesktopServices.openUrl`` used by
``src/dbs_annotator/utils/session_exporter.py``.

On desktop we delegate to ``webbrowser.open`` for ``file://`` URIs, which
hands off to the OS default handler -- exactly what the Qt path did. On
iOS/Android Toga exposes platform share-sheet APIs via
``app.platform.open_url`` / ``UIActivityViewController`` etc.; those need
to be wired per target when mobile builds exit PoC.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover -- types only
    import toga

logger = logging.getLogger(__name__)


def open_file(app: toga.App | None, path: Path) -> bool:
    """Open (or share) an exported file.

    Returns ``True`` if the request was dispatched successfully, ``False``
    if we could not find any working handler.
    """
    del app  # Reserved for future mobile share-sheet routing.
    p = Path(path)
    uri = p.resolve().as_uri()

    if sys.platform.startswith("ios") or sys.platform.startswith("android"):
        logger.info("No mobile share handler yet for %s", p)
        return False

    try:
        if webbrowser.open(uri):
            return True
    except Exception:  # noqa: BLE001
        logger.info("webbrowser.open failed for %s", uri)

    try:
        if sys.platform == "win32":
            import os

            os.startfile(str(p))  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(p)])  # noqa: S603
        else:
            subprocess.Popen(["xdg-open", str(p)])  # noqa: S603
        return True
    except Exception:  # noqa: BLE001
        logger.info("Could not open exported file: %s", p)
        return False
