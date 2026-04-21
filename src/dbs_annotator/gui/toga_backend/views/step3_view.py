"""Toga port of ``Step3View`` -- active session recording."""

from __future__ import annotations

import inspect
import logging
from collections.abc import Callable
from typing import Any

import toga
from toga.style.pack import COLUMN, ROW, Pack

from ....models import StimulationParameters
from .. import dialogs
from ..contacts import anode_cathode_tokens, apply_tokens_to_canvas
from ..theme import LIGHT
from ..widgets import (
    ElectrodeCanvas,
    GroupBox,
    ScaleProgress,
    StimParamsInput,
)
from ..widgets.stim_params import StimTriple

logger = logging.getLogger(__name__)

_CANVAS_SIZE = (168, 300)


class _ScaleRow(toga.Box):
    """One session scale row: label + ScaleProgress + ignore button."""

    def __init__(self, name: str, minimum: int, maximum: int) -> None:
        super().__init__(style=Pack(direction=ROW, margin_bottom=4))
        self.name = name
        self._disabled = False
        self.label = toga.Label(name, style=Pack(width=150, margin_right=6))
        self.progress = ScaleProgress(
            minimum=minimum,
            maximum=maximum,
            value=minimum,
            width=240,
            height=28,
            display_scale=1.0,
        )
        self.toggle = toga.Button(
            "N/A",
            on_press=self._toggle_na,
            style=Pack(margin_left=6, width=60),
        )
        self.add(self.label)
        self.add(self.progress)
        self.add(self.toggle)

    def _toggle_na(self, widget) -> None:
        self._disabled = not self._disabled
        self.progress.set_disabled(self._disabled)
        self.toggle.text = "Use" if self._disabled else "N/A"

    def get_value(self) -> str:
        if self._disabled:
            return "NaN"
        return str(self.progress.value)

    def reset(self) -> None:
        self._disabled = False
        self.toggle.text = "N/A"
        self.progress.set_disabled(False)


class Step3View(toga.Box):
    def __init__(
        self,
        window: toga.Window,
        *,
        on_back: Callable[[], None] | None = None,
        on_close_session: Callable[[], None] | None = None,
        on_insert: Callable[..., Any] | None = None,
        on_undo: Callable[..., Any] | None = None,
        on_export: Callable[[str], None] | None = None,
    ) -> None:
        _p = LIGHT
        super().__init__(
            style=Pack(
                direction=COLUMN,
                flex=1,
                margin_left=10,
                margin_right=10,
                margin_bottom=8,
            )
        )
        self._dialog_host = window
        self._on_back = on_back
        self._on_close = on_close_session
        self._on_insert = on_insert
        self._on_undo = on_undo
        self._on_export = on_export
        self._scale_rows: list[_ScaleRow] = []

        self.left_stim = StimParamsInput()
        self.right_stim = StimParamsInput()
        stim_left = GroupBox("Left stim", flex=1, palette=_p, margin=2)
        stim_left.body.add(self.left_stim)
        stim_right = GroupBox("Right stim", flex=1, palette=_p, margin=2)
        stim_right.body.add(self.right_stim)
        stim_row = toga.Box(style=Pack(direction=ROW, flex=0))
        stim_row.add(stim_left)
        stim_row.add(stim_right)

        cw, ch = _CANVAS_SIZE
        self.left_canvas = ElectrodeCanvas(width=cw, height=ch)
        self.right_canvas = ElectrodeCanvas(width=cw, height=ch)
        canvas_row = toga.Box(style=Pack(direction=ROW, flex=1))
        lc_group = GroupBox("Left electrode", flex=1, palette=_p, margin=2)
        lc_group.body.add(self.left_canvas)
        rc_group = GroupBox("Right electrode", flex=1, palette=_p, margin=2)
        rc_group.body.add(self.right_canvas)
        canvas_row.add(lc_group)
        canvas_row.add(rc_group)

        left_panel = toga.Box(style=Pack(direction=COLUMN, flex=3, margin_right=8))
        left_panel.add(stim_row)
        left_panel.add(canvas_row)

        self.scales_group = GroupBox("Session scales", flex=1, palette=_p, margin=2)
        self.notes = toga.MultilineTextInput(
            placeholder="Session notes...",
            style=Pack(flex=0, height=72),
        )
        notes_group = GroupBox("Session notes", flex=0, palette=_p, margin=2)
        notes_group.body.add(self.notes)

        right_panel = toga.Box(style=Pack(direction=COLUMN, flex=2))
        right_panel.add(self.scales_group)
        right_panel.add(notes_group)

        main_row = toga.Box(style=Pack(direction=ROW, flex=1))
        main_row.add(left_panel)
        main_row.add(right_panel)
        self.add(main_row)

        self.insert_button = toga.Button(
            "Insert",
            on_press=self._handle_insert,
            style=Pack(
                margin_right=6,
                width=120,
                background_color=_p.primary,
                color=_p.on_primary,
            ),
        )
        self.undo_button = toga.Button(
            "Undo",
            on_press=self._handle_undo,
            style=Pack(margin_right=6, width=88),
            enabled=False,
        )
        self.export_word_button = toga.Button(
            "Export Word",
            on_press=self._handle_export_word,
            style=Pack(margin_right=6, width=118),
        )
        self.export_pdf_button = toga.Button(
            "Export PDF",
            on_press=self._handle_export_pdf,
            style=Pack(margin_right=6, width=118),
        )
        self.close_button = toga.Button(
            "Close session",
            on_press=self._handle_close,
            style=Pack(width=128),
        )
        action_row = toga.Box(style=Pack(direction=ROW, margin_top=6, flex=0))
        action_row.add(self.insert_button)
        action_row.add(self.undo_button)
        action_row.add(self.export_word_button)
        action_row.add(self.export_pdf_button)
        action_row.add(self.close_button)

        self.back_button = toga.Button(
            "\u2190 Back",
            on_press=self._handle_back,
            style=Pack(width=112, margin_right=8),
        )
        nav = toga.Box(style=Pack(direction=ROW, margin_top=6))
        nav.add(self.back_button)

        self.add(action_row)
        self.add(nav)

    def get_header_title(self) -> str:
        return "Programming Session Ongoing"

    def get_header_subtitle(self) -> str:
        return "Step 3 of 3 - active recording"

    # ---- configuration API ----------------------------------------------

    def set_initial_state(
        self,
        model,
        stim: StimulationParameters,
        scale_defs: list[tuple[str, str, str]],
    ) -> None:
        if model is not None:
            self.left_canvas.set_model(model)
            self.right_canvas.set_model(model)
        apply_tokens_to_canvas(
            self.left_canvas, stim.left_anode or "", stim.left_cathode or ""
        )
        apply_tokens_to_canvas(
            self.right_canvas, stim.right_anode or "", stim.right_cathode or ""
        )

        def parse_amp(value: str | None) -> str:
            if not value:
                return ""
            if "_" in value:
                try:
                    return str(sum(float(p) for p in value.split("_") if p))
                except ValueError:
                    return ""
            return value

        self.left_stim.set_values(
            StimTriple(
                frequency=stim.left_frequency or "",
                amplitude=parse_amp(stim.left_amplitude),
                pulse_width=stim.left_pulse_width or "",
            )
        )
        self.right_stim.set_values(
            StimTriple(
                frequency=stim.right_frequency or "",
                amplitude=parse_amp(stim.right_amplitude),
                pulse_width=stim.right_pulse_width or "",
            )
        )
        self.set_scales(scale_defs)

    def set_scales(self, scale_defs: list[tuple[str, str, str]]) -> None:
        self.scales_group.clear()
        self._scale_rows = []
        for name, minv, maxv in scale_defs:
            try:
                lo = int(float(minv))
            except ValueError:
                lo = 0
            try:
                hi = int(float(maxv))
            except ValueError:
                hi = 10
            if hi <= lo:
                hi = lo + 1
            row = _ScaleRow(name, lo, hi)
            self._scale_rows.append(row)
            self.scales_group.body.add(row)

    def set_undo_enabled(self, enabled: bool) -> None:
        self.undo_button.enabled = enabled

    # ---- snapshots -------------------------------------------------------

    def get_stimulation(self) -> StimulationParameters:
        left = self.left_stim.get_values()
        right = self.right_stim.get_values()
        la, lc = anode_cathode_tokens(self.left_canvas)
        ra, rc = anode_cathode_tokens(self.right_canvas)
        return StimulationParameters(
            left_frequency=left.frequency,
            left_anode=la,
            left_cathode=lc,
            left_amplitude=left.amplitude,
            left_pulse_width=left.pulse_width,
            right_frequency=right.frequency,
            right_anode=ra,
            right_cathode=rc,
            right_amplitude=right.amplitude,
            right_pulse_width=right.pulse_width,
        )

    def get_scale_values(self) -> list[tuple[str, str]]:
        return [(row.name, row.get_value()) for row in self._scale_rows]

    def get_notes(self) -> str:
        return str(self.notes.value or "")

    def clear_notes(self) -> None:
        self.notes.value = ""
        for row in self._scale_rows:
            row.reset()

    # ---- handlers --------------------------------------------------------

    def _handle_back(self, widget) -> None:
        if self._on_back:
            self._on_back()

    async def _handle_insert(self, widget) -> None:
        if self._on_insert:
            r = self._on_insert()
            if inspect.isawaitable(r):
                await r

    async def _handle_undo(self, widget) -> None:
        ok = await dialogs.confirm(
            self._dialog_host,
            "Confirm Undo",
            "Delete the last session entry?",
        )
        if ok and self._on_undo:
            r = self._on_undo()
            if inspect.isawaitable(r):
                await r

    async def _handle_close(self, widget) -> None:
        ok = await dialogs.confirm(
            self._dialog_host,
            "Confirm Close Session",
            "Close the current session? File will be saved.",
        )
        if ok and self._on_close:
            self._on_close()

    def _handle_export_word(self, widget) -> None:
        if self._on_export:
            self._on_export("word")

    def _handle_export_pdf(self, widget) -> None:
        if self._on_export:
            self._on_export("pdf")
