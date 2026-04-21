"""Minimal electrode-model data needed by the PoC canvas.

This duplicates just enough of ``src/dbs_annotator/config_electrode_models.py``
so the PoC can live in its own Briefcase project without depending on the
main app package.
"""

from __future__ import annotations

from dataclasses import dataclass


class ContactState:
    OFF = 0
    ANODIC = 1
    CATHODIC = 2


@dataclass
class ElectrodeModel:
    name: str
    num_contacts: int
    contact_height: float
    contact_spacing: float
    lead_diameter: float
    is_directional: bool = False
    tip_contact: bool = False
    directional_levels: tuple[int, ...] | None = None

    @property
    def segments_per_level(self) -> int:
        return 3 if self.is_directional else 1

    def is_level_directional(self, level_idx: int) -> bool:
        if not self.is_directional:
            return False
        if self.directional_levels is not None:
            return level_idx in self.directional_levels
        return 0 < level_idx < self.num_contacts - 1


MODELS: dict[str, ElectrodeModel] = {
    "Medtronic 3389": ElectrodeModel(
        "Medtronic 3389", 4, 1.5, 0.5, 1.27, is_directional=False
    ),
    "Medtronic SenSight B33015": ElectrodeModel(
        "Medtronic SenSight B33015", 4, 1.5, 1.5, 1.27, is_directional=True
    ),
    "Boston Vercise Directed": ElectrodeModel(
        "Boston Vercise Directed",
        4,
        1.5,
        0.5,
        1.3,
        is_directional=True,
        tip_contact=True,
        directional_levels=(1, 2),
    ),
    "Boston Vercise Cartesia HX": ElectrodeModel(
        "Boston Vercise Cartesia HX",
        6,
        1.5,
        1.5,
        1.3,
        is_directional=True,
        tip_contact=True,
        directional_levels=(1, 2, 3, 4, 5),
    ),
}


def validate_configuration(
    contact_states: dict[tuple[int, int], int], case_state: int
) -> tuple[bool, str]:
    """Clinical validation rules (subset of the production app)."""
    if case_state == ContactState.CATHODIC:
        if any(s == ContactState.CATHODIC for s in contact_states.values()):
            return False, "CASE cathodic: no contact may be cathodic"
    if case_state == ContactState.ANODIC:
        if any(s == ContactState.ANODIC for s in contact_states.values()):
            return False, "CASE anodic: no contact may be anodic"
    has_cathodic = any(s == ContactState.CATHODIC for s in contact_states.values())
    has_anodic = case_state == ContactState.ANODIC or any(
        s == ContactState.ANODIC for s in contact_states.values()
    )
    if has_cathodic and not has_anodic:
        return False, "At least one anodic contact (or CASE) required"
    return True, ""
