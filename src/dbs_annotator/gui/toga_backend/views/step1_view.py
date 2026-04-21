"""Toga port of ``Step1View`` -- initial session setup.

Covers the same user flow as ``src/dbs_annotator/views/step1_view.py``:
file selection, electrode model + program, stim params per side,
clinical scales + notes. Uses Toga primitives + the reusable widgets in
``gui.toga_backend.widgets``.
"""

from __future__ import annotations

import csv
import logging
import os
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import toga
from toga.style.pack import COLUMN, ROW, Pack

from ....config import CLINICAL_SCALES_PRESETS, PLACEHOLDERS, PRESET_BUTTONS
from ....config_electrode_models import (
    ELECTRODE_MODELS,
    MANUFACTURERS,
    ContactState,
    get_all_manufacturers,
)
from ....models import StimulationParameters
from .. import dialogs
from ..contacts import anode_cathode_tokens, apply_tokens_to_canvas
from ..theme import LIGHT
from ..widgets import (
    ClinicalScalesEditor,
    ElectrodeCanvas,
    GroupBox,
    StimParamsInput,
)

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "Medtronic SenSight B33005"

# Qt layout keeps electrodes beside a narrow settings column; keep canvas
# small enough for 900px-tall windows without a vertical scroll area.
_CANVAS_SIZE = (168, 300)


class Step1View(toga.Box):
    """Step 1: Initial session configuration."""

    def __init__(
        self,
        window: toga.Window,
        *,
        on_next: Callable[[], None] | None = None,
    ) -> None:
        _p = LIGHT
        super().__init__(
            style=Pack(
                direction=ROW,
                flex=1,
                margin_left=10,
                margin_right=10,
                margin_bottom=8,
            )
        )
        # Never assign ``self._window`` on a ``toga.Box`` — that shadows
        # ``Widget._window`` and skips ``app.widgets`` registration when this
        # view is mounted, breaking later ``remove``/``clear``.
        self._dialog_host = window
        self._on_next = on_next
        self.current_file_mode: str | None = None
        self.next_block_id: int | None = None

        self.file_input = toga.TextInput(
            placeholder="Select or create a .tsv file...",
            readonly=True,
            style=Pack(flex=1, margin_right=6),
        )
        self.open_button = toga.Button(
            "Open",
            on_press=self._on_open_file,
            style=Pack(
                width=80,
                margin_right=4,
                background_color=_p.primary,
                color=_p.on_primary,
            ),
        )
        self.new_button = toga.Button(
            "New",
            on_press=self._on_new_file,
            style=Pack(width=80, background_color=_p.primary, color=_p.on_primary),
        )
        file_row = toga.Box(style=Pack(direction=ROW, margin_bottom=4))
        file_row.add(self.file_input)
        file_row.add(self.open_button)
        file_row.add(self.new_button)

        file_group = GroupBox("Session file", flex=0, palette=_p, margin=2)
        file_group.body.add(file_row)

        # electrode model + program
        self.manufacturer_select = toga.Selection(
            items=["All Manufacturers", *get_all_manufacturers()],
            on_change=self._on_manufacturer_changed,
            style=Pack(flex=1),
        )
        self.model_select = toga.Selection(
            items=sorted(ELECTRODE_MODELS.keys()),
            on_change=self._on_model_changed,
            style=Pack(flex=1),
        )
        self.program_select = toga.Selection(
            items=[
                "None",
                "Group A",
                "Group B",
                "Group C",
                "Group D",
            ],
            style=Pack(flex=1),
        )

        settings = GroupBox("Electrode & program", flex=0, palette=_p, margin=2)
        settings.body.add(self._labelled_row("Manufacturer:", self.manufacturer_select))
        settings.body.add(self._labelled_row("Model:", self.model_select))
        settings.body.add(self._labelled_row("Program:", self.program_select))

        # stim params — stacked like Qt sidebar (not two wide columns)
        self.left_stim = StimParamsInput()
        self.right_stim = StimParamsInput()
        stim_left = GroupBox("Left stim", flex=0, palette=_p, margin=2)
        stim_left.body.add(self.left_stim)
        stim_right = GroupBox("Right stim", flex=0, palette=_p, margin=2)
        stim_right.body.add(self.right_stim)
        stim_stack = toga.Box(style=Pack(direction=COLUMN, flex=0))
        stim_stack.add(stim_left)
        stim_stack.add(stim_right)

        cw, ch = _CANVAS_SIZE
        self.left_canvas = ElectrodeCanvas(width=cw, height=ch)
        self.right_canvas = ElectrodeCanvas(width=cw, height=ch)
        canvas_left = GroupBox("Left electrode", flex=1, palette=_p, margin=2)
        canvas_left.body.add(self.left_canvas)
        canvas_right = GroupBox("Right electrode", flex=1, palette=_p, margin=2)
        canvas_right.body.add(self.right_canvas)
        canvas_row = toga.Box(style=Pack(direction=ROW, flex=1))
        canvas_row.add(canvas_left)
        canvas_row.add(canvas_right)

        # Qt: file on top of left column; below = [settings+stim | electrodes]
        work_row = toga.Box(style=Pack(direction=ROW, flex=1, align_items="start"))
        sidebar = toga.Box(style=Pack(direction=COLUMN, flex=0, margin_right=6))
        sidebar.add(settings)
        sidebar.add(stim_stack)
        work_row.add(sidebar)
        work_row.add(canvas_row)

        left_col = toga.Box(style=Pack(direction=COLUMN, flex=3, margin_right=8))
        left_col.add(file_group)
        left_col.add(work_row)

        # Right column: scales + notes (Qt splitter right side)
        self.clinical_scales = ClinicalScalesEditor()
        self._preset_buttons: dict[str, toga.Button] = {}
        preset_row = toga.Box(style=Pack(direction=ROW, margin_bottom=4))
        preset_row.add(
            toga.Label("Presets:", style=Pack(margin_right=6, color=_p.subtle))
        )
        for name in PRESET_BUTTONS:
            btn = toga.Button(
                name,
                on_press=self._make_preset_handler(name),
                style=Pack(margin_right=3, width=64, height=32),
            )
            self._preset_buttons[name] = btn
            preset_row.add(btn)

        scales_group = GroupBox("Clinical scales", flex=1, palette=_p, margin=2)
        scales_group.body.add(preset_row)
        scales_group.body.add(self.clinical_scales)

        self.notes = toga.MultilineTextInput(
            placeholder="Initial notes...",
            style=Pack(flex=0, height=72),
        )
        notes_group = GroupBox("Initial notes", flex=0, palette=_p, margin=2)
        notes_group.body.add(self.notes)

        self.next_button = toga.Button(
            "Next \u2192",
            on_press=self._handle_next,
            style=Pack(
                width=128,
                margin_top=6,
                background_color=_p.primary,
                color=_p.on_primary,
            ),
        )
        next_row = toga.Box(style=Pack(direction=ROW, justify_content="end", flex=0))
        next_row.add(self.next_button)

        right_col = toga.Box(style=Pack(direction=COLUMN, flex=2))
        right_col.add(scales_group)
        right_col.add(notes_group)
        right_col.add(next_row)

        self.add(left_col)
        self.add(right_col)

        # sensible default model
        available = sorted(ELECTRODE_MODELS.keys())
        default = (
            _DEFAULT_MODEL
            if _DEFAULT_MODEL in available
            else (available[0] if available else "")
        )
        if default:
            self.model_select.value = default
            self._apply_model_by_name(default)

    def get_header_title(self) -> str:
        return "Clinical Programming Session Setup"

    def get_header_subtitle(self) -> str:
        return "Step 1 of 3 - initial settings"

    # ---- layout helpers --------------------------------------------------

    @staticmethod
    def _labelled_row(label: str, widget: toga.Widget) -> toga.Box:
        row = toga.Box(style=Pack(direction=ROW, margin_bottom=4))
        row.add(toga.Label(label, style=Pack(width=140, margin_right=4)))
        row.add(widget)
        return row

    # ---- events ----------------------------------------------------------

    def _on_manufacturer_changed(self, widget) -> None:
        manufacturer = str(widget.value or "All Manufacturers")
        if manufacturer == "All Manufacturers":
            items = sorted(ELECTRODE_MODELS.keys())
        else:
            items = list(MANUFACTURERS.get(manufacturer, []))
        self.model_select.items = items
        if items:
            self.model_select.value = items[0]
            self._apply_model_by_name(items[0])

    def _on_model_changed(self, widget) -> None:
        name = str(widget.value or "")
        if name:
            self._apply_model_by_name(name)

    def _apply_model_by_name(self, name: str) -> None:
        model = ELECTRODE_MODELS.get(name)
        if not model:
            return
        self.left_canvas.set_model(model)
        self.right_canvas.set_model(model)

    def _make_preset_handler(self, preset_name: str) -> Callable[[toga.Widget], None]:
        def handler(_w: toga.Widget) -> None:
            scales = CLINICAL_SCALES_PRESETS.get(preset_name, [])
            self.clinical_scales.set_items([(n, "") for n in scales])

        return handler

    async def _on_open_file(self, widget) -> None:
        path = await dialogs.open_file(
            self._dialog_host,
            "Open Existing TSV File",
            file_types=["tsv"],
        )
        if path is None:
            return
        self._load_existing_file(path)

    async def _on_new_file(self, widget) -> None:
        patient_id = await dialogs.ask_text(
            self._dialog_host,
            "New Session",
            "Patient ID:",
            default="01",
        )
        if patient_id is None:
            return
        run_num = await dialogs.ask_text(
            self._dialog_host,
            "New Session",
            "Run number:",
            default="01",
        )
        if run_num is None:
            return

        session_num = datetime.now().astimezone().strftime("%Y%m%d")
        default_name = (
            f"sub-{patient_id or '01'}_ses-{session_num}_task-programming"
            f"_run-{run_num or '01'}_events.tsv"
        )

        path = await dialogs.save_file(
            self._dialog_host,
            "Create New TSV File",
            suggested_name=default_name,
            file_types=["tsv"],
        )
        if path is None:
            return
        if path.suffix.lower() != ".tsv":
            path = path.with_suffix(".tsv")
        self.file_input.value = str(path)
        self.current_file_mode = "new"
        self.next_block_id = None

    def _load_existing_file(self, file_path: Path) -> None:
        """Restore the latest initial session from a .tsv file."""
        initial_rows: dict[int, dict] = {}
        max_session_id = -1
        max_block = -1
        latest_block_id = -1
        block0_scales: list[tuple[str, str]] = []

        try:
            with open(file_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter="\t")
                for row in reader:
                    try:
                        bid = int(float(row.get("block_id") or ""))
                    except (ValueError, TypeError):
                        continue
                    max_block = max(max_block, bid)
                    if row.get("is_initial") == "1":
                        try:
                            sid = int(float(row.get("session_ID") or ""))
                        except (ValueError, TypeError):
                            continue
                        if (
                            sid not in initial_rows
                            or bid > initial_rows[sid]["block_id"]
                        ):
                            initial_rows[sid] = {"row": row, "block_id": bid}
                        max_session_id = max(max_session_id, sid)

            if max_session_id >= 0 and max_session_id in initial_rows:
                latest = initial_rows[max_session_id]
                latest_block_id = latest["block_id"]
                with open(file_path, newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f, delimiter="\t")
                    for row in reader:
                        try:
                            sid = int(float(row.get("session_ID") or ""))
                            bid = int(float(row.get("block_id") or ""))
                        except (ValueError, TypeError):
                            continue
                        if (
                            sid == max_session_id
                            and bid == latest_block_id
                            and row.get("is_initial") == "1"
                        ):
                            name = row.get("scale_name") or ""
                            value = row.get("scale_value") or ""
                            if name:
                                block0_scales.append((name, str(value)))

        except OSError as e:
            logger.warning("Failed to read TSV %s: %s", file_path, e)
            return

        self.file_input.value = str(file_path)
        self.current_file_mode = "existing"
        self.next_block_id = max_block + 1 if max_block >= 0 else None

        if max_session_id >= 0 and max_session_id in initial_rows:
            latest_row = initial_rows[max_session_id]["row"]
            model_name = latest_row.get("electrode_model") or ""
            if model_name and model_name in ELECTRODE_MODELS:
                self.model_select.value = model_name
                self._apply_model_by_name(model_name)

            program = latest_row.get("program_ID") or latest_row.get("group_ID")
            if program:
                try:
                    self.program_select.value = program
                except ValueError:
                    pass

            self._load_stim_from_row(latest_row)

            # dedupe scales keeping last value
            seen: set[str] = set()
            deduped: list[tuple[str, str]] = []
            for n, v in reversed(block0_scales):
                if n not in seen:
                    seen.add(n)
                    deduped.append((n, v))
            self.clinical_scales.set_items(list(reversed(deduped)))

            notes_val = latest_row.get("notes") or ""
            self.notes.value = notes_val

    def _load_stim_from_row(self, row: dict) -> None:
        def parse(value: str) -> str:
            if not value:
                return ""
            if "_" in value:
                try:
                    return str(sum(float(p) for p in value.split("_") if p))
                except ValueError:
                    return ""
            return value

        from ..widgets.stim_params import StimTriple

        self.left_stim.set_values(
            StimTriple(
                frequency=row.get("left_stim_freq") or "",
                amplitude=parse(row.get("left_amplitude") or ""),
                pulse_width=row.get("left_pulse_width") or "",
            )
        )
        self.right_stim.set_values(
            StimTriple(
                frequency=row.get("right_stim_freq") or "",
                amplitude=parse(row.get("right_amplitude") or ""),
                pulse_width=row.get("right_pulse_width") or "",
            )
        )
        apply_tokens_to_canvas(
            self.left_canvas,
            row.get("left_anode") or "",
            row.get("left_cathode") or "",
        )
        apply_tokens_to_canvas(
            self.right_canvas,
            row.get("right_anode") or "",
            row.get("right_cathode") or "",
        )

    def _handle_next(self, widget) -> None:
        if self._on_next:
            self._on_next()

    # ---- snapshot API consumed by the flow -------------------------------

    def get_file_path(self) -> str:
        return (self.file_input.value or "").strip()

    def get_program(self) -> str:
        value = self.program_select.value or ""
        return "" if value in ("None", "") else str(value)

    def get_model_name(self) -> str:
        return str(self.model_select.value or "")

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

    def get_clinical_scales(self) -> list[tuple[str, str]]:
        return self.clinical_scales.items()

    def get_notes(self) -> str:
        return str(self.notes.value or "")

    # Expose PLACEHOLDERS for tests / future consumers.
    PLACEHOLDERS = PLACEHOLDERS
    CONTACT_OFF = ContactState.OFF
    DEFAULT_FILE_EXT = ".tsv"
    DEFAULT_FILE_DIR: str = os.getcwd()
