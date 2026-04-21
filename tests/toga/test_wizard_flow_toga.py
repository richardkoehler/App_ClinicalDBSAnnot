"""Smoke tests for the Toga wizard flow + view wiring.

Drives the wizard across its full navigation path using ``toga-dummy``
so we can cheaply catch regressions when widgets are added/removed.

Async flows (disk I/O off the event loop, prewarm tasks) require a single
``asyncio.run`` body so pending tasks complete before assertions.
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import toga

from dbs_annotator.gui.toga_backend.views.wizard_window import WizardWindow
from dbs_annotator.models import StimulationParameters


def _make_wizard(toga_app: toga.App) -> WizardWindow:
    """Build a fresh wizard + main window for the current test.

    The ``toga_app`` fixture is session-scoped so we can't rely on
    ``toga_app.main_window`` being empty: every test must install its
    own ``MainWindow`` and bind the wizard's content tree to it, which
    also triggers the widget-registry wiring required by ``body.add``.
    """
    wizard = WizardWindow(toga_app)
    main = toga.MainWindow(title="Test")
    main.content = wizard.content
    toga_app.main_window = main
    return wizard


def test_wizard_starts_on_step0(toga_app: toga.App) -> None:
    wizard = _make_wizard(toga_app)
    assert type(wizard.current_view).__name__ == "Step0View"


def test_full_workflow_navigation(tmp_path: Path, toga_app: toga.App) -> None:
    async def body() -> None:
        wizard = _make_wizard(toga_app)
        wizard._handle_full_mode()
        assert type(wizard.current_view).__name__ == "Step1View"

        file_path = tmp_path / "sub-01_ses-20260101_task-programming_run-01_events.tsv"
        wizard._step1.file_input.value = str(file_path)
        wizard._step1.current_file_mode = "new"
        wizard._step1.clinical_scales.set_items([("UPDRS", "20")])
        wizard._step1.notes.value = "initial"

        await wizard._handle_step1_next_async()
        assert type(wizard.current_view).__name__ == "Step2View"
        assert wizard.flow.session_data.is_file_open()

        wizard._step2.set_session_scales([("Tremor", "0", "10")])
        await wizard._handle_step2_next_async()
        assert type(wizard.current_view).__name__ == "Step3View"
        assert len(wizard._step3._scale_rows) == 1

        await wizard._step3_insert_async()
        assert wizard._step3.undo_button.enabled is True
        assert wizard.flow.session_data.block_id >= 1

        ok = await asyncio.to_thread(wizard.flow.undo_last_session_row)
        assert ok

        wizard.flow.close_session()

    asyncio.run(body())


def test_annotations_workflow_navigation(tmp_path: Path, toga_app: toga.App) -> None:
    async def body() -> None:
        wizard = _make_wizard(toga_app)
        wizard._handle_annotations_mode()
        assert type(wizard.current_view).__name__ == "AnnotationsFileView"

        file_path = tmp_path / "sub-99_ses-20260101_task-notes_run-01_events.tsv"
        wizard._annot_file.file_input.value = str(file_path)
        wizard._annot_file.current_file_mode = "new"

        await wizard._handle_annot_next_async()
        assert type(wizard.current_view).__name__ == "AnnotationsSessionView"

        await wizard._annot_insert_async("first note")
        await wizard._annot_insert_async("second note")

        wizard.flow.close_session()
        assert file_path.exists()

    asyncio.run(body())


def test_wizard_flow_stim_snapshot(toga_app: toga.App) -> None:
    wizard = _make_wizard(toga_app)
    wizard._handle_full_mode()
    stim = wizard._step1.get_stimulation()
    assert isinstance(stim, StimulationParameters)


def test_step3_scale_rows_na_toggle(tmp_path: Path, toga_app: toga.App) -> None:
    async def body() -> None:
        wizard = _make_wizard(toga_app)
        wizard._handle_full_mode()
        with tempfile.NamedTemporaryFile(
            suffix=".tsv", dir=tmp_path, delete=False
        ) as tmp:
            path = Path(tmp.name)
        wizard._step1.file_input.value = str(path)
        wizard._step1.current_file_mode = "new"
        await wizard._handle_step1_next_async()
        wizard._step2.set_session_scales([("X", "0", "5"), ("Y", "0", "10")])
        await wizard._handle_step2_next_async()

        row = wizard._step3._scale_rows[0]
        row._toggle_na(None)
        assert row.get_value() == "NaN"
        row._toggle_na(None)
        assert row.get_value() != "NaN"
        wizard.flow.close_session()

    asyncio.run(body())
