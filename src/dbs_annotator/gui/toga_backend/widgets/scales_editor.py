"""Dynamic editors for clinical + session scales.

Port of the dynamic rows pattern from ``Step1View`` and ``Step2View``.
The Qt version hand-rolls add/remove via ``QHBoxLayout`` + ``QLineEdit``
widgets; we reproduce the same behaviour with a ``toga.Box`` of rows.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

import toga
from toga.style.pack import COLUMN, ROW, Pack


class ClinicalScaleRow(toga.Box):
    """One scale row: ``name`` + ``score`` + remove button."""

    def __init__(
        self,
        *,
        name: str = "",
        value: str = "",
        on_remove: Callable[[ClinicalScaleRow], None] | None = None,
    ) -> None:
        super().__init__(style=Pack(direction=ROW, margin_bottom=4))
        self.name_input = toga.TextInput(
            value=name, placeholder="Scale", style=Pack(flex=2, margin_right=4)
        )
        self.value_input = toga.TextInput(
            value=value, placeholder="Score", style=Pack(flex=1, margin_right=4)
        )
        self.remove_btn = toga.Button(
            "-",
            on_press=lambda _w: on_remove(self) if on_remove else None,
            style=Pack(width=32),
        )
        self.add(self.name_input)
        self.add(self.value_input)
        self.add(self.remove_btn)

    def get(self) -> tuple[str, str]:
        return (self.name_input.value or "").strip(), (
            self.value_input.value or ""
        ).strip()


class ClinicalScalesEditor(toga.Box):
    """List of ``ClinicalScaleRow`` + an ``Add`` button."""

    def __init__(self) -> None:
        super().__init__(style=Pack(direction=COLUMN, flex=1))
        self.rows_box = toga.Box(style=Pack(direction=COLUMN))
        self.add(self.rows_box)
        self.add_btn = toga.Button(
            "+ Add scale",
            on_press=self._on_add_clicked,
            style=Pack(margin_top=4, width=120),
        )
        self.add(self.add_btn)
        self._rows: list[ClinicalScaleRow] = []

    def _on_add_clicked(self, widget) -> None:
        self.append()

    def append(self, name: str = "", value: str = "") -> ClinicalScaleRow:
        row = ClinicalScaleRow(name=name, value=value, on_remove=self._remove_row)
        self._rows.append(row)
        self.rows_box.add(row)
        return row

    def _remove_row(self, row: ClinicalScaleRow) -> None:
        if row not in self._rows:
            return
        self._rows.remove(row)
        self.rows_box.remove(row)

    def set_items(self, items: Iterable[tuple[str, str]]) -> None:
        while self._rows:
            self._remove_row(self._rows[0])
        for name, value in items:
            self.append(name, value)

    def items(self) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        for row in self._rows:
            name, value = row.get()
            if name:
                out.append((name, value))
        return out


class SessionScaleRow(toga.Box):
    """One row: ``name`` + ``min`` + ``max`` + remove button."""

    def __init__(
        self,
        *,
        name: str = "",
        min_value: str = "0",
        max_value: str = "10",
        on_remove: Callable[[SessionScaleRow], None] | None = None,
    ) -> None:
        super().__init__(style=Pack(direction=ROW, margin_bottom=4))
        self.name_input = toga.TextInput(
            value=name, placeholder="Scale", style=Pack(flex=2, margin_right=4)
        )
        self.min_input = toga.TextInput(
            value=min_value, placeholder="Min", style=Pack(flex=1, margin_right=4)
        )
        self.max_input = toga.TextInput(
            value=max_value, placeholder="Max", style=Pack(flex=1, margin_right=4)
        )
        self.remove_btn = toga.Button(
            "-",
            on_press=lambda _w: on_remove(self) if on_remove else None,
            style=Pack(width=32),
        )
        self.add(self.name_input)
        self.add(self.min_input)
        self.add(self.max_input)
        self.add(self.remove_btn)

    def get(self) -> tuple[str, str, str]:
        return (
            (self.name_input.value or "").strip(),
            (self.min_input.value or "").strip(),
            (self.max_input.value or "").strip(),
        )


class SessionScalesEditor(toga.Box):
    def __init__(self) -> None:
        super().__init__(style=Pack(direction=COLUMN, flex=1))
        self.rows_box = toga.Box(style=Pack(direction=COLUMN))
        self.add(self.rows_box)
        self.add_btn = toga.Button(
            "+ Add scale",
            on_press=self._on_add_clicked,
            style=Pack(margin_top=4, width=120),
        )
        self.add(self.add_btn)
        self._rows: list[SessionScaleRow] = []

    def _on_add_clicked(self, widget) -> None:
        self.append()

    def append(
        self, name: str = "", min_value: str = "0", max_value: str = "10"
    ) -> SessionScaleRow:
        row = SessionScaleRow(
            name=name,
            min_value=min_value,
            max_value=max_value,
            on_remove=self._remove_row,
        )
        self._rows.append(row)
        self.rows_box.add(row)
        return row

    def _remove_row(self, row: SessionScaleRow) -> None:
        if row not in self._rows:
            return
        self._rows.remove(row)
        self.rows_box.remove(row)

    def set_items(self, items: Iterable[tuple[str, str, str]]) -> None:
        while self._rows:
            self._remove_row(self._rows[0])
        for name, minv, maxv in items:
            self.append(name, minv, maxv)

    def items(self) -> list[tuple[str, str, str]]:
        out: list[tuple[str, str, str]] = []
        for row in self._rows:
            name, minv, maxv = row.get()
            if name:
                out.append((name, minv or "0", maxv or "10"))
        return out
