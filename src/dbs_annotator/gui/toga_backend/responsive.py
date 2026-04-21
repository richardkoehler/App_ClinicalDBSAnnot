"""Responsive layout helpers for the Toga build.

Toga has no CSS-style media queries; we observe window size and emit
``LayoutMode`` values that views can switch on. The Qt version of this
(``src/dbs_annotator/utils/responsive.py``) uses ``QScreen`` geometry
and is tied to Qt types, so we keep that file intact for the Qt build
and provide a backend-neutral replacement here.

Breakpoints (width in logical pixels):

* ``MOBILE`` -- w < 600 (phone portrait)
* ``TABLET`` -- 600 <= w < 960 (tablet portrait / phone landscape)
* ``DESKTOP`` -- w >= 960 (anything bigger)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum


class LayoutMode(Enum):
    MOBILE = "mobile"
    TABLET = "tablet"
    DESKTOP = "desktop"


MOBILE_MAX = 600
TABLET_MAX = 960


def classify(width: int) -> LayoutMode:
    if width < MOBILE_MAX:
        return LayoutMode.MOBILE
    if width < TABLET_MAX:
        return LayoutMode.TABLET
    return LayoutMode.DESKTOP


@dataclass
class BreakpointObserver:
    """Debounced window-size observer for a Toga window.

    Usage::

        obs = BreakpointObserver(on_change=view.apply_layout)
        main_window.on_resize = obs.handle_resize
    """

    on_change: Callable[[LayoutMode], None]
    _current: LayoutMode | None = None

    def handle_resize(self, *, width: int, **_: object) -> None:
        mode = classify(int(width))
        if mode is not self._current:
            self._current = mode
            self.on_change(mode)

    @property
    def current(self) -> LayoutMode | None:
        return self._current
