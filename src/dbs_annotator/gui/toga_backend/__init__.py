"""Toga implementation of ``dbs_annotator.gui`` interfaces.

Selected in the forthcoming mobile/desktop unified build. During Phase 2
the Qt backend is still the active one; this package exists so views can
be ported incrementally without disturbing the live Qt app.

Use :func:`install` once, before any code calls ``dbs_annotator.gui.get_*``.
"""

from __future__ import annotations

from .bootstrap import install

__all__ = ["install"]
