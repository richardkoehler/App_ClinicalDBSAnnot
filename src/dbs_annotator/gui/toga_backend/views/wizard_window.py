"""Toga ``WizardWindow`` -- owns the step navigation for both workflows.

Holds the backend-neutral :class:`WizardFlow`, routes user actions across
``Step0View`` -> ``Step1View`` -> ``Step2View`` -> ``Step3View`` (full
workflow) and ``Step0View`` -> ``AnnotationsFileView`` ->
``AnnotationsSessionView`` (annotation-only workflow).
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Coroutine
from pathlib import Path
from typing import TYPE_CHECKING, Any

import toga
from toga.style.pack import COLUMN, ROW, Pack

from ....config_electrode_models import ELECTRODE_MODELS
from .. import dialogs
from ..theme import LIGHT
from ..wizard_flow import WizardFlow
from .annotation_only_view import AnnotationsFileView, AnnotationsSessionView
from .step0_view import Step0View
from .step1_view import Step1View
from .step2_view import Step2View
from .step3_view import Step3View

if TYPE_CHECKING:  # pragma: no cover
    pass

logger = logging.getLogger(__name__)


class WizardWindow:
    def __init__(self, app: toga.App) -> None:
        self._app = app
        self.flow = WizardFlow()

        _p = LIGHT
        self.header_title = toga.Label(
            "DBS Annotator",
            style=Pack(
                font_size=20,
                font_weight="bold",
                margin_bottom=2,
                color=_p.primary,
            ),
        )
        self.header_subtitle = toga.Label(
            "", style=Pack(color=_p.subtle, margin_bottom=4)
        )
        header = toga.Box(
            style=Pack(
                direction=ROW,
                margin_top=14,
                margin_bottom=12,
                margin_left=20,
                margin_right=20,
                background_color=_p.primary_bg,
            )
        )
        header_titles = toga.Box(style=Pack(direction=COLUMN, flex=1))
        header_titles.add(self.header_title)
        header_titles.add(self.header_subtitle)
        header.add(header_titles)

        # Exactly one stack child at a time (``QStackedWidget`` parity). WinForms
        # ignores ``Pack.display=NONE``, so visibility toggling left every step
        # on-screen; reparent with ``remove`` / ``add`` instead.
        self._stack = toga.Box(style=Pack(direction=COLUMN, flex=1))
        self._body = toga.Box(style=Pack(direction=COLUMN, flex=1))
        self.content = toga.Box(
            style=Pack(direction=COLUMN, flex=1, background_color=_p.surface)
        )
        self.content.add(header)
        self.content.add(self._body)
        self._body.add(self._stack)

        # ---- views --------------------------------------------------------
        self._step0 = Step0View(
            on_full_mode=self._handle_full_mode,
            on_annotations_only=self._handle_annotations_mode,
            on_longitudinal_report=self._handle_longitudinal,
        )
        self._step1: Step1View | None = None
        self._step2: Step2View | None = None
        self._step3: Step3View | None = None
        self._annot_file: AnnotationsFileView | None = None
        self._annot_session: AnnotationsSessionView | None = None
        self._step3_prewarm_task: asyncio.Task[None] | None = None

        self.current_view: toga.Box = self._step0
        self._stack.add(self._step0)
        self._apply_headers(self._step0)

    @staticmethod
    def _schedule(coro: Coroutine[Any, Any, None]) -> None:
        """Run ``coro`` on the app loop, or block with ``asyncio.run`` (e.g. tests)."""
        try:
            asyncio.get_running_loop().create_task(coro)
        except RuntimeError:
            asyncio.run(coro)

    # ---- nav helpers -----------------------------------------------------

    def _show(self, view: toga.Box) -> None:
        """Single visible step: one child on ``_stack`` (WinForms-safe)."""
        if (
            view is self.current_view
            and len(self._stack.children) == 1
            and self._stack.children[0] is view
        ):
            self._apply_headers(view)
            return
        for ch in list(self._stack.children):
            self._stack.remove(ch)
        self._stack.add(view)
        self.current_view = view
        self._apply_headers(view)

    def _apply_headers(self, view: toga.Box) -> None:
        title = getattr(view, "get_header_title", lambda: "")()
        subtitle = getattr(view, "get_header_subtitle", lambda: "")()
        if title:
            self.header_title.text = title
        self.header_subtitle.text = subtitle

    @property
    def window(self) -> toga.Window:
        main = self._app.main_window
        assert isinstance(main, toga.Window)
        return main

    # ---- step0 handlers --------------------------------------------------

    def _handle_full_mode(self) -> None:
        if self._step1 is None:
            self._step1 = Step1View(
                self.window,
                on_next=lambda: self._schedule(self._handle_step1_next_async()),
            )
        self._show(self._step1)

    def _handle_annotations_mode(self) -> None:
        if self._annot_file is None:
            self._annot_file = AnnotationsFileView(
                self.window,
                on_next=lambda: self._schedule(self._handle_annot_next_async()),
                on_back=self._back_to_step0,
            )
        self._show(self._annot_file)

    def _handle_longitudinal(self) -> None:
        asyncio.ensure_future(
            dialogs.info(
                self.window,
                "Longitudinal Report",
                "Longitudinal reports are available in the desktop Qt build. "
                "A Toga-native report tool is on the roadmap.",
            )
        )

    def _back_to_step0(self) -> None:
        self._show(self._step0)

    # ---- full workflow ---------------------------------------------------

    def _create_step3(self) -> Step3View:
        return Step3View(
            self.window,
            on_back=self._back_to_step2,
            on_close_session=self._close_full_session,
            on_insert=self._step3_insert_async,
            on_undo=self._step3_undo_async,
            on_export=self._step3_export,
        )

    async def _prewarm_step3_async(self) -> None:
        await asyncio.sleep(0)
        if self._step3 is None:
            self._step3 = self._create_step3()

    async def _handle_step1_next_async(self) -> None:
        assert self._step1 is not None
        step1 = self._step1

        file_path = step1.get_file_path()
        if not file_path:
            await dialogs.warn(
                self.window, "Missing file", "Select a file path to save."
            )
            return

        self.flow.state.file_path = file_path
        self.flow.state.file_mode = step1.current_file_mode
        self.flow.state.next_block_id = step1.next_block_id
        self.flow.state.electrode_model_name = step1.get_model_name()
        self.flow.state.model = ELECTRODE_MODELS.get(step1.get_model_name())
        self.flow.state.program = step1.get_program()

        stim = step1.get_stimulation()
        scales = step1.get_clinical_scales()
        notes = step1.get_notes()
        try:
            await asyncio.to_thread(self.flow.commit_step1, stim, scales, notes)
        except (OSError, ValueError) as e:
            logger.exception("Step 1 commit failed")
            await dialogs.error(self.window, "Error", f"Failed to save: {e}")
            return

        if self._step2 is None:
            self._step2 = Step2View(
                on_back=self._back_to_step1,
                on_next=lambda: self._schedule(self._handle_step2_next_async()),
            )
        self._show(self._step2)
        self._step3_prewarm_task = asyncio.create_task(self._prewarm_step3_async())

    def _back_to_step1(self) -> None:
        if self._step1 is not None:
            self._show(self._step1)

    async def _handle_step2_next_async(self) -> None:
        assert self._step2 is not None
        if self._step3_prewarm_task is not None:
            t = self._step3_prewarm_task
            self._step3_prewarm_task = None
            if not t.done():
                try:
                    await t
                except Exception:
                    logger.exception("Step 3 prewarm failed")
        if self._step3 is None:
            self._step3 = self._create_step3()

        self.flow.state.session_scales = self._step2.get_session_scales()
        self._step3.set_initial_state(
            self.flow.state.model,
            self.flow.state.initial_stim,
            self.flow.state.session_scales,
        )
        self._show(self._step3)

    def _back_to_step2(self) -> None:
        if self._step2 is not None:
            self._show(self._step2)

    async def _step3_insert_async(self) -> None:
        assert self._step3 is not None
        stim = self._step3.get_stimulation()
        scale_values = self._step3.get_scale_values()
        notes = self._step3.get_notes()
        try:
            await asyncio.to_thread(
                self.flow.commit_session_row, stim, scale_values, notes
            )
        except (OSError, ValueError) as e:
            logger.exception("Session row insert failed")
            await dialogs.error(self.window, "Error", f"Insert failed: {e}")
            return
        self._step3.clear_notes()
        self._step3.set_undo_enabled(True)

    async def _step3_undo_async(self) -> None:
        assert self._step3 is not None
        ok = await asyncio.to_thread(self.flow.undo_last_session_row)
        if not ok:
            await dialogs.warn(self.window, "Undo", "No entries to undo.")
            return
        if self.flow.session_data.block_id == 0:
            self._step3.set_undo_enabled(False)

    def _step3_export(self, fmt: str) -> None:
        asyncio.ensure_future(self._run_export_session(fmt))

    async def _run_export_session(self, fmt: str) -> None:
        exporter = self.flow.session_exporter
        if exporter is None:
            await dialogs.info(
                self.window,
                "Export",
                "Export requires the desktop Qt build for rich reports. "
                "The underlying .tsv is always saved.",
            )
            return
        try:
            if fmt == "word":
                await asyncio.to_thread(exporter.export_to_word, None)
            else:
                await asyncio.to_thread(exporter.export_to_pdf, None)
            await dialogs.info(self.window, "Export", f"{fmt.upper()} export complete.")
        except Exception as e:  # pragma: no cover -- best-effort
            logger.exception("Export failed")
            await dialogs.error(self.window, "Export failed", str(e))

    def _close_full_session(self) -> None:
        self.flow.close_session()
        self._back_to_step0()

    # ---- annotations-only workflow ---------------------------------------

    async def _handle_annot_next_async(self) -> None:
        assert self._annot_file is not None
        file_path = self._annot_file.get_file_path()
        if not file_path:
            await dialogs.warn(self.window, "Missing File", "Select a file path.")
            return

        mode = self._annot_file.current_file_mode

        def _open_annot_storage() -> None:
            if mode == "new":
                self.flow.session_data.initialize_simple_file(file_path)
            elif mode == "existing":
                self.flow.session_data.open_simple_file_append(file_path)
            else:
                if os.path.exists(file_path):
                    self.flow.session_data.open_simple_file_append(file_path)
                else:
                    self.flow.session_data.initialize_simple_file(file_path)

        try:
            await asyncio.to_thread(_open_annot_storage)
        except OSError as e:
            await dialogs.error(self.window, "Error", f"Failed to init file: {e}")
            return

        if self._annot_session is None:
            self._annot_session = AnnotationsSessionView(
                self.window,
                on_insert=self._annot_insert_async,
                on_close_session=self._close_annot_session,
                on_export=self._annot_export,
            )
        self._show(self._annot_session)

    async def _annot_insert_async(self, text: str) -> None:
        try:
            await asyncio.to_thread(
                self.flow.session_data.write_simple_annotation, text
            )
        except (OSError, ValueError) as e:
            logger.exception("Annotation insert failed")
            await dialogs.error(self.window, "Error", f"Insert failed: {e}")

    def _annot_export(self, fmt: str) -> None:
        asyncio.ensure_future(self._run_export_annot(fmt))

    async def _run_export_annot(self, fmt: str) -> None:
        exporter = self.flow.session_exporter
        if exporter is None:
            await dialogs.info(
                self.window,
                "Export",
                "Rich export requires the Qt build. TSV remains saved.",
            )
            return
        try:
            if fmt == "word":
                await asyncio.to_thread(exporter.export_annotations_to_word, None)
            else:
                await asyncio.to_thread(exporter.export_annotations_to_pdf, None)
            await dialogs.info(self.window, "Export", f"{fmt.upper()} export complete.")
        except Exception as e:  # pragma: no cover
            logger.exception("Annotation export failed")
            await dialogs.error(self.window, "Export failed", str(e))

    def _close_annot_session(self) -> None:
        self.flow.close_session()
        self._back_to_step0()

    # ---- for tests -------------------------------------------------------

    def debug_paths(self) -> dict[str, Path | None]:
        return {
            "file_path": (
                Path(self.flow.state.file_path) if self.flow.state.file_path else None
            )
        }
