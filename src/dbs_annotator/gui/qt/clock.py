"""Qt-side re-export of the backend-neutral :class:`SystemClock`.

Kept for import-compat while callers migrate to
``dbs_annotator.gui.clock.SystemClock``.
"""

from __future__ import annotations

from ..clock import SystemClock

__all__ = ["SystemClock"]
