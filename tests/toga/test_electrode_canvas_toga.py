"""Behavioural tests for the Toga ``ElectrodeCanvas`` port.

Mirrors the Qt test suite in
``tests/unit/test_electrode_canvas.py``. These tests focus on state
transitions and hit testing -- the actual pixel output of
``toga.Canvas`` is backend-specific and covered by visual QA on each
target per ``poc/GO_NO_GO.md``.
"""

from __future__ import annotations

import pytest

from dbs_annotator.config_electrode_models import (
    BOSTON_VERCISE_CARTESIA_HX,
    MEDTRONIC_3389,
    ContactState,
)
from dbs_annotator.gui.toga_backend.widgets.electrode_canvas import (
    ElectrodeCanvas,
    _point_in_polygon,
    _point_in_rect,
)


@pytest.fixture
def canvas():
    return ElectrodeCanvas(model=MEDTRONIC_3389, width=260, height=560)


def test_cycle_contact_goes_off_anodic_cathodic_off(canvas):
    cid = (0, 0)
    assert canvas.contact_states.get(cid, ContactState.OFF) == ContactState.OFF
    canvas._cycle_contact(cid)
    assert canvas.contact_states[cid] == ContactState.ANODIC
    canvas._cycle_contact(cid)
    assert canvas.contact_states[cid] == ContactState.CATHODIC
    canvas._cycle_contact(cid)
    assert cid not in canvas.contact_states


def test_cycle_case_cycles_three_states(canvas):
    assert canvas.case_state == ContactState.OFF
    canvas._cycle_case()
    assert canvas.case_state == ContactState.ANODIC
    canvas._cycle_case()
    assert canvas.case_state == ContactState.CATHODIC
    canvas._cycle_case()
    assert canvas.case_state == ContactState.OFF


def test_set_model_resets_contact_states(canvas):
    canvas._cycle_contact((0, 0))
    canvas._cycle_case()
    canvas.set_model(BOSTON_VERCISE_CARTESIA_HX)
    assert canvas.contact_states == {}
    assert canvas.case_state == ContactState.OFF
    assert canvas.model is BOSTON_VERCISE_CARTESIA_HX


def test_ring_cycle_promotes_all_segments_together():
    canvas = ElectrodeCanvas(model=BOSTON_VERCISE_CARTESIA_HX)
    canvas._cycle_ring(1)
    for seg in range(3):
        assert canvas.contact_states[(1, seg)] == ContactState.ANODIC
    canvas._cycle_ring(1)
    for seg in range(3):
        assert canvas.contact_states[(1, seg)] == ContactState.CATHODIC
    canvas._cycle_ring(1)
    for seg in range(3):
        assert (1, seg) not in canvas.contact_states


def test_ring_cycle_is_no_op_on_non_directional_model():
    canvas = ElectrodeCanvas(model=MEDTRONIC_3389)
    before = dict(canvas.contact_states)
    canvas._cycle_ring(1)
    assert canvas.contact_states == before


def test_validation_callback_fires_on_state_change():
    events: list[tuple[bool, str]] = []
    canvas = ElectrodeCanvas(
        model=MEDTRONIC_3389, on_validation=lambda ok, msg: events.append((ok, msg))
    )
    canvas._cycle_contact((0, 0))
    assert events, "validation callback should have fired"
    ok, _ = events[-1]
    assert isinstance(ok, bool)


def test_point_in_polygon_square():
    square = [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert _point_in_polygon(5, 5, square)
    assert not _point_in_polygon(20, 20, square)


def test_point_in_rect_with_padding():
    rect = (10, 10, 40, 40)
    assert _point_in_rect(8, 8, rect, pad=5)
    assert not _point_in_rect(2, 2, rect, pad=5)
