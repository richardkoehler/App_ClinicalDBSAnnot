"""Behavioural tests for the Toga ``ScaleProgress`` port."""

from __future__ import annotations

from dbs_annotator.gui.toga_backend.widgets.scale_progress import ScaleProgress


def test_set_value_clamps_to_range():
    s = ScaleProgress(minimum=0, maximum=40, value=10, width=100, height=28)
    s.set_value(-5)
    assert s.value == 0
    s.set_value(999)
    assert s.value == 40


def test_on_change_fires_only_on_new_value():
    events: list[int] = []
    s = ScaleProgress(
        minimum=0,
        maximum=40,
        value=10,
        on_change=events.append,
        width=100,
        height=28,
    )
    s.set_value(10)
    assert events == [], "no change should fire no event"
    s.set_value(20)
    assert events == [20]


def test_drag_handler_updates_value():
    s = ScaleProgress(minimum=0, maximum=40, value=0, width=100, height=28)
    s._w = 100
    s._on_press(s.canvas, 50, 10)
    assert s.value == 20
    s._on_drag(s.canvas, 100, 10)
    assert s.value == 40
    s._on_release(s.canvas, 100, 10)
    # Further drag after release must NOT change the value.
    s._on_drag(s.canvas, 0, 10)
    assert s.value == 40


def test_disabled_blocks_press_and_drag():
    s = ScaleProgress(minimum=0, maximum=40, value=0, width=100, height=28)
    s.set_disabled(True)
    s._w = 100
    s._on_press(s.canvas, 50, 10)
    assert s.value == 0
