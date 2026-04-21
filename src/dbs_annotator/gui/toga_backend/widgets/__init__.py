"""Toga-backend reusable widgets.

These are production-grade ports of the Qt-side widgets in
``src/dbs_annotator/ui``. They share the same behavioural contract (same
signals/slots via plain Python callables) so they can be dropped into
the migrated views in Phase 2.
"""

from __future__ import annotations

from .electrode_canvas import ElectrodeCanvas
from .file_chooser import FileChooser
from .group_box import GroupBox
from .increment import IncrementWidget
from .scale_progress import ScaleProgress
from .scales_editor import (
    ClinicalScaleRow,
    ClinicalScalesEditor,
    SessionScaleRow,
    SessionScalesEditor,
)
from .stim_params import StimParamsInput, StimTriple

__all__ = [
    "ClinicalScaleRow",
    "ClinicalScalesEditor",
    "ElectrodeCanvas",
    "FileChooser",
    "GroupBox",
    "IncrementWidget",
    "ScaleProgress",
    "SessionScaleRow",
    "SessionScalesEditor",
    "StimParamsInput",
    "StimTriple",
]
