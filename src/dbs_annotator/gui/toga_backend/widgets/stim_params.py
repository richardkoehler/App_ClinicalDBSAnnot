"""Frequency / amplitude / pulse-width input group (left or right side).

Ports the repeated Qt layout in ``Step1View._create_settings_group``:
three rows of ``QLabel`` + ``IncrementWidget``. The Toga version reuses
``IncrementWidget`` which already mirrors Qt's up/down button pair.
"""

from __future__ import annotations

from dataclasses import dataclass

import toga
from toga.style.pack import COLUMN, ROW, Pack

from ....config import STIMULATION_LIMITS
from .increment import IncrementWidget


@dataclass
class StimTriple:
    frequency: str = ""
    amplitude: str = ""
    pulse_width: str = ""


class StimParamsInput(toga.Box):
    """Three rows: frequency, amplitude, pulse-width."""

    def __init__(self, *, title: str | None = None) -> None:
        super().__init__(style=Pack(direction=COLUMN, flex=1))
        if title:
            self.add(toga.Label(title, style=Pack(font_weight="bold", margin_bottom=4)))

        freq_lim = STIMULATION_LIMITS["frequency"]
        amp_lim = STIMULATION_LIMITS["amplitude"]
        pw_lim = STIMULATION_LIMITS["pulse_width"]

        self.freq = IncrementWidget(
            value=float(freq_lim.get("min", 10)),
            step1=float(freq_lim["step1"]),
            step2=float(freq_lim.get("step2", 0)) or None,
            decimals=0,
            min_value=float(freq_lim["min"]),
            max_value=float(freq_lim["max"]),
            width=150,
        )
        self.amp = IncrementWidget(
            value=float(amp_lim.get("min", 0.0)),
            step1=float(amp_lim["step1"]),
            step2=float(amp_lim.get("step2", 0)) or None,
            decimals=int(amp_lim.get("decimals", 2)),
            min_value=float(amp_lim["min"]),
            max_value=float(amp_lim["max"]),
            width=150,
        )
        self.pw = IncrementWidget(
            value=float(pw_lim.get("min", 10)),
            step1=float(pw_lim["step1"]),
            step2=float(pw_lim.get("step2", 0)) or None,
            decimals=0,
            min_value=float(pw_lim["min"]),
            max_value=float(pw_lim["max"]),
            width=150,
        )

        self.add(self._row("Frequency (Hz):", self.freq))
        self.add(self._row("Amplitude (mA):", self.amp))
        self.add(self._row("Pulse width (\u00b5s):", self.pw))

    @staticmethod
    def _row(label: str, widget: toga.Widget) -> toga.Box:
        row = toga.Box(style=Pack(direction=ROW, margin_bottom=2))
        row.add(toga.Label(label, style=Pack(width=118, margin_right=4)))
        row.add(widget)
        return row

    def get_values(self) -> StimTriple:
        return StimTriple(
            frequency=self._fmt_int(self.freq.value),
            amplitude=f"{self.amp.value:.2f}".rstrip("0").rstrip("."),
            pulse_width=self._fmt_int(self.pw.value),
        )

    def set_values(self, triple: StimTriple) -> None:
        if triple.frequency:
            try:
                self.freq.set_value(float(triple.frequency))
            except ValueError:
                pass
        if triple.amplitude:
            try:
                self.amp.set_value(float(self._parse_amplitude(triple.amplitude)))
            except ValueError:
                pass
        if triple.pulse_width:
            try:
                self.pw.set_value(float(triple.pulse_width))
            except ValueError:
                pass

    @staticmethod
    def _fmt_int(v: float) -> str:
        return str(int(round(v)))

    @staticmethod
    def _parse_amplitude(value: str) -> float:
        """Handle split-amplitude values ``"2.5_2.5"`` by summing segments."""
        if "_" in value:
            parts = [p for p in value.split("_") if p.strip()]
            try:
                return sum(float(p) for p in parts)
            except ValueError:
                return 0.0
        return float(value)
