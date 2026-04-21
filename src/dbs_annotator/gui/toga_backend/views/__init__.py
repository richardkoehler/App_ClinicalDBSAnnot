"""Toga ports of the views under ``src/dbs_annotator/views``.

During Phase 2 the Qt views remain the production path; files here land
incrementally. The migration order (mirroring the plan in
``docs/developer/toga_migration.md``) is:

1. ``step0_view`` -- welcome / mode selection (small, safest to port first)
2. ``wizard_window`` -- shell navigation (uses toga.OptionContainer)
3. ``annotation_only_view``
4. ``step1_view`` -- the biggest; depends on the widgets under
   ``gui/toga_backend/widgets`` being stable.
5. ``step2_view``
6. ``step3_view``
7. ``export_dialog``
8. ``longitudinal_report_view``

Each port keeps parity with its Qt source by delegating to the same
controllers (``controllers/wizard_controller.py``) which already talk in
plain-Python domain types -- no Qt required.
"""

from __future__ import annotations

from .annotation_only_view import AnnotationsFileView, AnnotationsSessionView
from .step0_view import Step0View
from .step1_view import Step1View
from .step2_view import Step2View
from .step3_view import Step3View
from .wizard_window import WizardWindow

__all__ = [
    "AnnotationsFileView",
    "AnnotationsSessionView",
    "Step0View",
    "Step1View",
    "Step2View",
    "Step3View",
    "WizardWindow",
]
