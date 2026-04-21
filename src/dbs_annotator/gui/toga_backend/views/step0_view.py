"""Toga port of ``src/dbs_annotator/views/step0_view.py``.

Mode-selection landing page. Ported as the template for the remaining
views -- the pattern is:

* inherit from ``toga.Box`` (Toga's generic container);
* expose Pythonic callbacks (``on_full_mode``, ``on_annotations_only``,
  ``on_longitudinal_report``) matching the signal names in the Qt version
  so the controller/wizard code can treat both backends uniformly.
"""

from __future__ import annotations

from collections.abc import Callable

import toga
from toga.style.pack import CENTER, COLUMN, ROW, Pack

from ..theme import LIGHT


class Step0View(toga.Box):
    def __init__(
        self,
        *,
        on_full_mode: Callable[[], None] | None = None,
        on_annotations_only: Callable[[], None] | None = None,
        on_longitudinal_report: Callable[[], None] | None = None,
    ) -> None:
        _p = LIGHT
        super().__init__(
            style=Pack(
                direction=COLUMN,
                margin_top=16,
                margin_bottom=16,
                margin_left=24,
                margin_right=24,
                flex=1,
            )
        )
        self._on_full_mode = on_full_mode
        self._on_annotations_only = on_annotations_only
        self._on_longitudinal_report = on_longitudinal_report

        self.add(
            toga.Label(
                "New session",
                style=Pack(
                    font_size=16,
                    font_weight="bold",
                    margin_bottom=8,
                    color=_p.primary,
                ),
            )
        )

        notes_row = toga.Box(
            style=Pack(direction=ROW, align_items=CENTER, margin_bottom=12)
        )
        self.full_mode_button = toga.Button(
            "Complete workflow",
            on_press=self._handle_full_mode,
            style=Pack(
                margin_right=15,
                width=220,
                background_color=_p.primary,
                color=_p.on_primary,
            ),
        )
        self.annotations_only_button = toga.Button(
            "Annotation-only workflow",
            on_press=self._handle_annotations_only,
            style=Pack(
                margin_left=15,
                width=220,
                background_color=_p.primary,
                color=_p.on_primary,
            ),
        )
        notes_row.add(self.full_mode_button)
        notes_row.add(self.annotations_only_button)
        self.add(notes_row)

        self.add(toga.Divider(style=Pack(margin_top=8, margin_bottom=8)))

        self.add(
            toga.Label(
                "Longitudinal Report",
                style=Pack(
                    font_size=16,
                    font_weight="bold",
                    margin_bottom=8,
                    color=_p.primary,
                ),
            )
        )
        longitudinal_row = toga.Box(style=Pack(direction=ROW, align_items=CENTER))
        self.longitudinal_report_button = toga.Button(
            "Create Longitudinal Report",
            on_press=self._handle_longitudinal,
            style=Pack(width=260),
        )
        longitudinal_row.add(self.longitudinal_report_button)
        self.add(longitudinal_row)

    def get_header_title(self) -> str:
        return "DBS Annotator"

    def get_header_subtitle(self) -> str:
        return "Record and analyze deep brain stimulation programming sessions"

    def _handle_full_mode(self, widget) -> None:
        if self._on_full_mode is not None:
            self._on_full_mode()

    def _handle_annotations_only(self, widget) -> None:
        if self._on_annotations_only is not None:
            self._on_annotations_only()

    def _handle_longitudinal(self, widget) -> None:
        if self._on_longitudinal_report is not None:
            self._on_longitudinal_report()
