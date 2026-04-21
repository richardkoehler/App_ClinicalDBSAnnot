"""Titled container mimicking ``QGroupBox``.

Toga has no native group-box, so we build one with a bold title label and
a divider above the contents. Default styling uses :mod:`theme` so the
Toga build picks up the same blue accent + tinted panels as the Qt QSS.
"""

from __future__ import annotations

import toga
from toga.style.pack import COLUMN, Pack

from ..theme import LIGHT, Palette


class GroupBox(toga.Box):
    def __init__(
        self,
        title: str,
        *,
        flex: int = 0,
        margin: int = 4,
        padding: int = 6,
        palette: Palette = LIGHT,
    ) -> None:
        super().__init__(
            style=Pack(
                direction=COLUMN,
                margin=margin,
                flex=flex,
                background_color=palette.primary_bg,
            )
        )
        self.title_label = toga.Label(
            title,
            style=Pack(
                font_weight="bold",
                margin_bottom=2,
                color=palette.primary,
            ),
        )
        self.body = toga.Box(
            style=Pack(
                direction=COLUMN,
                margin_top=2,
                margin_bottom=padding,
                margin_left=padding,
                margin_right=padding,
                flex=1,
            )
        )
        self.add(self.title_label)
        self.add(
            toga.Box(
                style=Pack(
                    height=2,
                    margin_bottom=4,
                    background_color=palette.separator,
                )
            )
        )
        self.add(self.body)

    def set_title(self, title: str) -> None:
        self.title_label.text = title

    def clear(self) -> None:
        while self.body.children:
            self.body.remove(self.body.children[0])
