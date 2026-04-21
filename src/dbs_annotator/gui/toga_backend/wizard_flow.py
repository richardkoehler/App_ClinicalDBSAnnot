"""Toga wizard flow manager.

This plays the role of ``WizardController`` for the Toga backend, but
stays free of Qt imports. It owns the ``SessionData`` instance and the
in-flight session state that the Toga views read/write.

The existing Qt controller in ``src/dbs_annotator/controllers/``
remains the source of truth for the Qt build; duplicating the glue
here avoids importing PySide6 on mobile targets.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ...config_electrode_models import ContactState, ElectrodeModel
from ...models import ClinicalScale, SessionData, SessionScale, StimulationParameters


@dataclass
class ElectrodeState:
    """Snapshot of contact/case selections for one side."""

    contact_states: dict[tuple[int, int], int] = field(default_factory=dict)
    case_state: int = ContactState.OFF
    enabled: bool = True


@dataclass
class WizardState:
    file_path: str = ""
    file_mode: str | None = None  # "new" | "existing" | None
    next_block_id: int | None = None

    electrode_model_name: str = ""
    model: ElectrodeModel | None = None
    program: str = "None"

    left: ElectrodeState = field(default_factory=ElectrodeState)
    right: ElectrodeState = field(default_factory=ElectrodeState)

    initial_stim: StimulationParameters = field(default_factory=StimulationParameters)
    session_stim: StimulationParameters = field(default_factory=StimulationParameters)

    clinical_scales: list[tuple[str, str]] = field(default_factory=list)
    session_scales: list[tuple[str, str, str]] = field(default_factory=list)
    initial_notes: str = ""
    session_notes: str = ""


class WizardFlow:
    """Mutable container driving the Toga wizard."""

    def __init__(self) -> None:
        self.session_data = SessionData()
        self.state = WizardState()
        self._session_exporter = None

    @property
    def session_exporter(self):
        if self._session_exporter is None:
            try:
                from ...utils.session_exporter import SessionExporter

                self._session_exporter = SessionExporter(self.session_data)
            except Exception:  # pragma: no cover -- Qt-only deps missing
                self._session_exporter = None
        return self._session_exporter

    # ---- file management -------------------------------------------------

    def open_initial_file(self) -> None:
        if self.session_data.is_file_open():
            return
        if not self.state.file_path:
            raise ValueError("No file path selected.")
        if self.state.file_mode == "existing":
            self.session_data.open_file_append(
                self.state.file_path, start_block_id=self.state.next_block_id
            )
        else:
            self.session_data.open_file(self.state.file_path)

    def close_session(self) -> None:
        self.session_data.close_file()

    # ---- step 1 ----------------------------------------------------------

    def commit_step1(
        self,
        stim: StimulationParameters,
        scales: list[tuple[str, str]],
        notes: str,
    ) -> None:
        """Write the step-1 clinical row to TSV."""
        self.open_initial_file()

        self.state.initial_stim = stim
        self.state.clinical_scales = scales
        self.state.initial_notes = notes
        self.state.session_stim = stim.copy()

        clinical = [ClinicalScale(name=n, value=v) for n, v in scales if n]

        self.session_data.write_clinical_scales(
            clinical,
            stim,
            group=self.state.program or "",
            electrode_model=self.state.electrode_model_name or "",
            notes=notes,
        )

    # ---- step 3 ----------------------------------------------------------

    def commit_session_row(
        self,
        stim: StimulationParameters,
        scale_values: list[tuple[str, str]],
        notes: str,
    ) -> None:
        self.state.session_stim = stim
        self.state.session_notes = notes

        sess_scales = [
            SessionScale(name=n, current_value=v) for n, v in scale_values if n
        ]

        self.session_data.write_session_scales(
            sess_scales,
            stim,
            group=self.state.program or "",
            electrode_model=self.state.electrode_model_name or "",
            notes=notes,
        )

    def undo_last_session_row(self) -> bool:
        """Remove the last inserted TSV block. Returns ``True`` on success."""
        import csv

        if not self.session_data.is_file_open():
            return False
        last_block = self.session_data.block_id - 1
        if last_block < 0:
            return False

        file_path = self.session_data.file_path
        if not file_path:
            return False

        rows_to_keep = []
        removed = 0
        with open(file_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            fieldnames = list(reader.fieldnames or [])
            for row in reader:
                try:
                    bid = int(row.get("block_id", ""))
                except (ValueError, TypeError):
                    rows_to_keep.append(row)
                    continue
                if bid == last_block:
                    removed += 1
                else:
                    rows_to_keep.append(row)
        if removed == 0:
            return False

        self.session_data.block_id = last_block
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
            writer.writeheader()
            writer.writerows(rows_to_keep)
        return True
