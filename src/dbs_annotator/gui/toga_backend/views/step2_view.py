"""Toga port of ``Step2View`` -- session scales definition."""

from __future__ import annotations

from collections.abc import Callable

import toga
from toga.style.pack import COLUMN, ROW, Pack

from ....config import PRESET_BUTTONS, SESSION_SCALES_PRESETS
from ..theme import LIGHT
from ..widgets import GroupBox, SessionScalesEditor


class Step2View(toga.Box):
    def __init__(
        self,
        *,
        on_back: Callable[[], None] | None = None,
        on_next: Callable[[], None] | None = None,
    ) -> None:
        _p = LIGHT
        super().__init__(style=Pack(direction=COLUMN, flex=1, margin=12))
        self._on_back = on_back
        self._on_next = on_next

        self.session_scales = SessionScalesEditor()

        preset_row = toga.Box(style=Pack(direction=ROW, margin_bottom=6))
        preset_row.add(
            toga.Label("Presets:", style=Pack(margin_right=6, color=_p.subtle))
        )
        for name in PRESET_BUTTONS:
            preset_row.add(
                toga.Button(
                    name,
                    on_press=self._make_preset_handler(name),
                    style=Pack(margin_right=4, width=66, height=32),
                )
            )

        group = GroupBox("Session scales", flex=1, palette=_p)
        group.body.add(preset_row)
        group.body.add(self.session_scales)

        nav = toga.Box(style=Pack(direction=ROW, margin_top=8))
        self.back_button = toga.Button(
            "\u2190 Back",
            on_press=self._handle_back,
            style=Pack(width=120, margin_right=8),
        )
        self.next_button = toga.Button(
            "Next \u2192",
            on_press=self._handle_next,
            style=Pack(width=120, background_color=_p.primary, color=_p.on_primary),
        )
        nav.add(self.back_button)
        nav.add(self.next_button)

        self.add(group)
        self.add(nav)

    def get_header_title(self) -> str:
        return "Session Scales"

    def get_header_subtitle(self) -> str:
        return "Step 2 of 3 - define tracking scales"

    def _make_preset_handler(self, preset_name: str) -> Callable[[toga.Widget], None]:
        def handler(_w: toga.Widget) -> None:
            self.session_scales.set_items(SESSION_SCALES_PRESETS.get(preset_name, []))

        return handler

    def _handle_back(self, widget) -> None:
        if self._on_back:
            self._on_back()

    def _handle_next(self, widget) -> None:
        if self._on_next:
            self._on_next()

    def get_session_scales(self) -> list[tuple[str, str, str]]:
        return self.session_scales.items()

    def set_session_scales(self, items: list[tuple[str, str, str]]) -> None:
        self.session_scales.set_items(items)
