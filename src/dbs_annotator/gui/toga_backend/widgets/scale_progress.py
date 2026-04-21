"""Toga port of the Qt ``ScaleProgressWidget``.

The Qt version is a ``QProgressBar`` with an event filter that turns
press/drag into value changes. Toga has no direct equivalent, so we
rebuild the same UX on a ``toga.Canvas``. Drag latency on Android is one
of the PoC's go/no-go gates.
"""

from __future__ import annotations

from collections.abc import Callable

import toga
from toga.colors import rgb
from toga.style.pack import Pack

_TRACK = rgb(235, 235, 240)
_TRACK_BORDER = rgb(180, 180, 190)
_FILL = rgb(72, 132, 232)
_FILL_DISABLED = rgb(190, 190, 195)
_TEXT = rgb(30, 30, 30)


class ScaleProgress(toga.Box):
    def __init__(
        self,
        *,
        minimum: int = 0,
        maximum: int = 40,
        value: int = 0,
        height: int = 28,
        width: int = 220,
        on_change: Callable[[int], None] | None = None,
        display_scale: float = 0.25,
    ) -> None:
        super().__init__(style=Pack(direction="row", width=width, height=height))
        self._min = int(minimum)
        self._max = int(maximum)
        self._value = int(value)
        self._w = int(width)
        self._h = int(height)
        self._display_scale = display_scale
        self._on_change = on_change
        self._dragging = False
        self._disabled = False

        self.canvas = toga.Canvas(
            style=Pack(flex=1, width=width, height=height),
            on_press=self._on_press,
            on_drag=self._on_drag,
            on_release=self._on_release,
            on_resize=self._on_resize,
        )
        self.add(self.canvas)
        self._repaint()

    @property
    def value(self) -> int:
        return self._value

    def set_value(self, v: int) -> None:
        v = max(self._min, min(self._max, int(v)))
        if v != self._value:
            self._value = v
            if self._on_change is not None:
                self._on_change(v)
            self._repaint()

    def set_disabled(self, disabled: bool) -> None:
        self._disabled = bool(disabled)
        self._repaint()

    def _on_press(self, widget, x: float, y: float, **_: object) -> None:
        if self._disabled:
            return
        self._dragging = True
        self._set_from_x(x)

    def _on_drag(self, widget, x: float, y: float, **_: object) -> None:
        if self._dragging and not self._disabled:
            self._set_from_x(x)

    def _on_release(self, widget, x: float, y: float, **_: object) -> None:
        self._dragging = False

    def _on_resize(self, widget, width: int, height: int, **_: object) -> None:
        self._w = max(1, int(width))
        self._h = max(1, int(height))
        self._repaint()

    def _set_from_x(self, x: float) -> None:
        if self._w <= 0:
            return
        t = max(0.0, min(1.0, float(x) / float(self._w)))
        new_val = int(round(self._min + t * (self._max - self._min)))
        self.set_value(new_val)

    def _repaint(self) -> None:
        ctx = self.canvas.context
        ctx.clear()

        track = (0.5, 0.5, max(0, self._w - 1), max(1, self._h - 1))
        with ctx.Fill(color=_TRACK) as fill:
            fill.rect(*track)
        with ctx.Stroke(color=_TRACK_BORDER, line_width=1) as stroke:
            stroke.rect(*track)

        if self._max > self._min:
            frac = (self._value - self._min) / float(self._max - self._min)
        else:
            frac = 0.0
        bar_w = max(0.0, min(1.0, frac)) * (self._w - 2)
        with ctx.Fill(color=_FILL_DISABLED if self._disabled else _FILL) as fill:
            fill.rect(1, 1, bar_w, self._h - 2)

        display_val = self._value * self._display_scale
        label = f"{display_val:.2f}"
        with ctx.Fill(color=_TEXT) as text_fill:
            text_fill.write_text(
                label,
                self._w / 2 - 18,
                self._h / 2 + 4,
                font=toga.Font(family="sans-serif", size=11, weight="bold"),
            )

        self.canvas.redraw()
