"""Toga port of the Qt ``IncrementWidget``.

Combines a ``toga.TextInput`` with up/down buttons. Validation is done
in Python (``QDoubleValidator``/``QIntValidator`` have no Toga
equivalent). The caller supplies ``on_change`` which receives the parsed
float value every time the user commits (arrow press or focus-out).
"""

from __future__ import annotations

from collections.abc import Callable

import toga
from toga.style.pack import ROW, Pack


class IncrementWidget(toga.Box):
    def __init__(
        self,
        *,
        value: float = 0.0,
        step1: float = 0.5,
        step2: float | None = None,
        decimals: int = 2,
        min_value: float | None = None,
        max_value: float | None = None,
        width: int = 140,
        on_change: Callable[[float], None] | None = None,
    ) -> None:
        super().__init__(style=Pack(direction=ROW, width=width))
        self._step1 = step1
        self._step2 = step2
        self._decimals = decimals
        self._min = min_value
        self._max = max_value
        self._on_change = on_change
        self._value = self._clamp(value)

        self.line = toga.TextInput(
            value=self._format(self._value),
            on_change=self._on_text_change,
            style=Pack(flex=1),
        )

        self.inc1 = toga.Button("+", on_press=lambda w: self._bump(+self._step1))
        self.dec1 = toga.Button("-", on_press=lambda w: self._bump(-self._step1))

        self.add(self.dec1)
        self.add(self.line)
        self.add(self.inc1)

        if step2 is not None:
            self.inc2 = toga.Button("++", on_press=lambda w: self._bump(+step2))
            self.dec2 = toga.Button("--", on_press=lambda w: self._bump(-step2))
            self.add(self.inc2)
            # Put the coarse decrement first for symmetry.
            self.children.insert(0, self.dec2)

    @property
    def value(self) -> float:
        return self._value

    def set_value(self, v: float) -> None:
        v = self._clamp(v)
        if v == self._value:
            return
        self._value = v
        self.line.value = self._format(v)
        if self._on_change is not None:
            self._on_change(v)

    def _bump(self, delta: float) -> None:
        self.set_value(self._value + delta)

    def _on_text_change(self, widget) -> None:
        try:
            parsed = float(widget.value)
        except (TypeError, ValueError):
            return
        self.set_value(parsed)

    def _clamp(self, v: float) -> float:
        if self._min is not None:
            v = max(self._min, v)
        if self._max is not None:
            v = min(self._max, v)
        return v

    def _format(self, v: float) -> str:
        return f"{v:.{self._decimals}f}"
