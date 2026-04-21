"""Toga port of ``AnnotationsFileView`` + ``AnnotationsSessionView``.

Simplified workflow: choose a file then record timestamped text
annotations.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from datetime import datetime
from typing import Any

import toga
from toga.style.pack import COLUMN, ROW, Pack

from .. import dialogs
from ..widgets import GroupBox


class AnnotationsFileView(toga.Box):
    """Pick existing or new TSV for the annotation-only mode."""

    def __init__(
        self,
        window: toga.Window,
        *,
        on_next: Callable[[], None] | None = None,
        on_back: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(style=Pack(direction=COLUMN, flex=1, margin=12))
        self._dialog_host = window
        self._on_next = on_next
        self._on_back = on_back
        self.current_file_mode: str | None = None

        self.file_input = toga.TextInput(
            placeholder="Select or create a .tsv file...",
            readonly=True,
            style=Pack(flex=1, margin_right=6),
        )
        self.open_button = toga.Button(
            "Open", on_press=self._on_open, style=Pack(width=80, margin_right=4)
        )
        self.new_button = toga.Button(
            "New", on_press=self._on_new, style=Pack(width=80)
        )
        row = toga.Box(style=Pack(direction=ROW, margin_bottom=6))
        row.add(self.file_input)
        row.add(self.open_button)
        row.add(self.new_button)

        group = GroupBox("Annotation file", flex=0)
        group.body.add(row)

        nav = toga.Box(style=Pack(direction=ROW, margin_top=8))
        self.back_button = toga.Button(
            "\u2190 Back",
            on_press=self._handle_back,
            style=Pack(width=120, margin_right=8),
        )
        self.next_button = toga.Button(
            "Next \u2192",
            on_press=self._handle_next,
            style=Pack(width=120),
        )
        nav.add(self.back_button)
        nav.add(self.next_button)

        self.add(group)
        self.add(nav)

    def get_header_title(self) -> str:
        return "Annotation-only Workflow"

    def get_header_subtitle(self) -> str:
        return "Step 1 of 2 - select or create file"

    async def _on_open(self, widget) -> None:
        path = await dialogs.open_file(
            self._dialog_host, "Open TSV File", file_types=["tsv"]
        )
        if path is None:
            return
        self.file_input.value = str(path)
        self.current_file_mode = "existing"

    async def _on_new(self, widget) -> None:
        patient_id = await dialogs.ask_text(
            self._dialog_host, "New Session", "Patient ID:", default="01"
        )
        if patient_id is None:
            return
        run_num = await dialogs.ask_text(
            self._dialog_host, "New Session", "Run number:", default="01"
        )
        if run_num is None:
            return

        session_num = datetime.now().astimezone().strftime("%Y%m%d")
        suggested = (
            f"sub-{patient_id or '01'}_ses-{session_num}_task-notes"
            f"_run-{run_num or '01'}_events.tsv"
        )
        path = await dialogs.save_file(
            self._dialog_host,
            "Create Annotation File",
            suggested_name=suggested,
            file_types=["tsv"],
        )
        if path is None:
            return
        if path.suffix.lower() != ".tsv":
            path = path.with_suffix(".tsv")
        self.file_input.value = str(path)
        self.current_file_mode = "new"

    def _handle_back(self, widget) -> None:
        if self._on_back:
            self._on_back()

    def _handle_next(self, widget) -> None:
        if self._on_next:
            self._on_next()

    def get_file_path(self) -> str:
        return (self.file_input.value or "").strip()


class AnnotationsSessionView(toga.Box):
    """Record timestamped annotations into the selected file."""

    def __init__(
        self,
        window: toga.Window,
        *,
        on_insert: Callable[..., Any] | None = None,
        on_close_session: Callable[[], None] | None = None,
        on_export: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(style=Pack(direction=COLUMN, flex=1, margin=12))
        self._dialog_host = window
        self._on_insert = on_insert
        self._on_close = on_close_session
        self._on_export = on_export

        self.annotation_input = toga.MultilineTextInput(
            placeholder="Type an annotation...",
            style=Pack(flex=1, height=220),
        )
        group = GroupBox("Annotation", flex=1)
        group.body.add(self.annotation_input)

        self.insert_button = toga.Button(
            "Insert",
            on_press=self._handle_insert,
            style=Pack(width=140, margin_right=6),
        )
        self.export_word_button = toga.Button(
            "Export Word",
            on_press=self._handle_export_word,
            style=Pack(width=140, margin_right=6),
        )
        self.export_pdf_button = toga.Button(
            "Export PDF",
            on_press=self._handle_export_pdf,
            style=Pack(width=140, margin_right=6),
        )
        self.close_button = toga.Button(
            "Close session",
            on_press=self._handle_close,
            style=Pack(width=140),
        )
        actions = toga.Box(style=Pack(direction=ROW, margin_top=8))
        actions.add(self.insert_button)
        actions.add(self.export_word_button)
        actions.add(self.export_pdf_button)
        actions.add(self.close_button)

        self.add(group)
        self.add(actions)

    def get_header_title(self) -> str:
        return "Recording Annotations"

    def get_header_subtitle(self) -> str:
        return "Step 2 of 2 - insert timestamped notes"

    async def _handle_insert(self, widget) -> None:
        text = str(self.annotation_input.value or "").strip()
        if not text:
            return
        if self._on_insert:
            r = self._on_insert(text)
            if inspect.isawaitable(r):
                await r
        self.annotation_input.value = ""

    def _handle_export_word(self, widget) -> None:
        if self._on_export:
            self._on_export("word")

    def _handle_export_pdf(self, widget) -> None:
        if self._on_export:
            self._on_export("pdf")

    async def _handle_close(self, widget) -> None:
        ok = await dialogs.confirm(
            self._dialog_host,
            "Confirm Close",
            "Close the current session?",
        )
        if ok and self._on_close:
            self._on_close()
