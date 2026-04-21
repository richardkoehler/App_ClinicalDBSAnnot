"""A Step-1-like form that exercises Toga's native input widgets.

Validates that we can reproduce the controls currently built in
``src/dbs_annotator/views/step1_view.py``:

* combo box (Selection) for electrode model,
* numeric inputs with validation (replacing QDoubleValidator/QIntValidator),
* save-file dialog (replacing QFileDialog.getSaveFileName),
* drag-enabled scale slider (replacing the QProgressBar-based
  ScaleProgressWidget),
* electrode canvas embedded alongside the form.

The form is intentionally small -- it is a feasibility test, not the real
step-1 UI.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

import toga
from toga.style.pack import COLUMN, ROW, Pack

from .canvas_electrode import ElectrodeCanvas
from .canvas_scale import ScaleProgress
from .electrode_models import MODELS


def _parse_float(
    value: str, *, low: float, high: float
) -> tuple[bool, float | None, str]:
    if value.strip() == "":
        return False, None, "required"
    try:
        f = float(value)
    except ValueError:
        return False, None, "not a number"
    if f < low or f > high:
        return False, None, f"must be in [{low}, {high}]"
    return True, f, ""


class FormStep(toga.Box):
    def __init__(
        self,
        *,
        on_export_docx: Callable[[Path, dict], None],
        on_export_pdf: Callable[[Path, dict], None],
        request_save_path: Callable[[str, str], Coroutine[Any, Any, Path | None]],
    ) -> None:
        super().__init__(
            style=Pack(direction=ROW, flex=1, margin=12),
        )
        self._on_export_docx = on_export_docx
        self._on_export_pdf = on_export_pdf
        self._request_save_path = request_save_path

        self._model_names = list(MODELS.keys())
        default_model = MODELS[self._model_names[0]]

        # Left column -- form controls ------------------------------------
        self.selection = toga.Selection(
            items=self._model_names,
            on_change=self._on_model_change,
        )
        self.amp_input = toga.TextInput(placeholder="Amplitude (mA)", value="1.50")
        self.freq_input = toga.TextInput(placeholder="Frequency (Hz)", value="130")
        self.pw_input = toga.TextInput(placeholder="Pulse width (us)", value="60")

        self.amp_error = toga.Label("", style=Pack(color="#c42b2b", margin_top=2))
        self.freq_error = toga.Label("", style=Pack(color="#c42b2b", margin_top=2))
        self.pw_error = toga.Label("", style=Pack(color="#c42b2b", margin_top=2))

        self.scale = ScaleProgress(
            minimum=0, maximum=40, value=10, on_change=self._on_scale_change
        )
        self.scale_label = toga.Label("Clinical scale: 2.50")

        self.validation_label = toga.Label(
            "Configuration: OK", style=Pack(margin_top=6, color="#2a7a3b")
        )

        export_row = toga.Box(style=Pack(direction=ROW, margin_top=10))
        export_row.add(
            toga.Button(
                "Export DOCX",
                on_press=self._handle_export_docx,
                style=Pack(margin_right=6),
            )
        )
        export_row.add(toga.Button("Export PDF", on_press=self._handle_export_pdf))

        form_col = toga.Box(style=Pack(direction=COLUMN, flex=1, margin=8))
        form_col.add(toga.Label("Electrode model", style=Pack(margin_bottom=2)))
        form_col.add(self.selection)
        form_col.add(toga.Divider(style=Pack(margin_top=10, margin_bottom=10)))
        form_col.add(toga.Label("Amplitude (mA) [0-10]"))
        form_col.add(self.amp_input)
        form_col.add(self.amp_error)
        form_col.add(toga.Label("Frequency (Hz) [2-250]", style=Pack(margin_top=4)))
        form_col.add(self.freq_input)
        form_col.add(self.freq_error)
        form_col.add(toga.Label("Pulse width (us) [20-450]", style=Pack(margin_top=4)))
        form_col.add(self.pw_input)
        form_col.add(self.pw_error)
        form_col.add(toga.Divider(style=Pack(margin_top=10, margin_bottom=10)))
        form_col.add(self.scale_label)
        form_col.add(self.scale)
        form_col.add(self.validation_label)
        form_col.add(export_row)

        # Right column -- electrode canvas -------------------------------
        self.canvas = ElectrodeCanvas(
            model=default_model,
            on_validation=self._on_canvas_validation,
            width=260,
            height=620,
        )

        self.add(form_col)
        self.add(self.canvas)

    # event handlers ---------------------------------------------------

    def _on_model_change(self, widget) -> None:
        name = self.selection.value
        if name in MODELS:
            self.canvas.set_model(MODELS[name])

    def _on_scale_change(self, value: int) -> None:
        self.scale_label.text = f"Clinical scale: {value * 0.25:.2f}"

    def _on_canvas_validation(self, ok: bool, msg: str) -> None:
        if ok:
            self.validation_label.text = "Configuration: OK"
            self.validation_label.style.color = "#2a7a3b"
        else:
            self.validation_label.text = f"Invalid: {msg}"
            self.validation_label.style.color = "#c42b2b"

    def _validate_all(self) -> tuple[bool, dict]:
        ok_amp, amp, err_amp = _parse_float(self.amp_input.value, low=0, high=10)
        ok_freq, freq, err_freq = _parse_float(self.freq_input.value, low=2, high=250)
        ok_pw, pw, err_pw = _parse_float(self.pw_input.value, low=20, high=450)
        self.amp_error.text = "" if ok_amp else err_amp
        self.freq_error.text = "" if ok_freq else err_freq
        self.pw_error.text = "" if ok_pw else err_pw
        return all((ok_amp, ok_freq, ok_pw)), {
            "model": self.selection.value,
            "amplitude_mA": amp,
            "frequency_Hz": freq,
            "pulse_width_us": pw,
            "scale": self.scale.value * 0.25,
        }

    async def _handle_export_docx(self, widget) -> None:
        ok, data = self._validate_all()
        if not ok:
            return
        path = await self._request_save_path("Export DOCX", "dbs_session_report.docx")
        if path is not None:
            self._on_export_docx(Path(str(path)), data)

    async def _handle_export_pdf(self, widget) -> None:
        ok, data = self._validate_all()
        if not ok:
            return
        path = await self._request_save_path("Export PDF", "dbs_session_report.pdf")
        if path is not None:
            self._on_export_pdf(Path(str(path)), data)
