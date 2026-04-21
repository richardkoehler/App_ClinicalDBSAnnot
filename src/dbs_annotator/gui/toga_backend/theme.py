"""Colour tokens replacing the QSS themes.

The Qt build ships ``src/dbs_annotator/styles/{dark,light}_theme.qss``
(14 KB each). Toga has no QSS -- styling is done per-widget via ``Pack``
attributes and the widget's ``color`` / ``background_color`` properties.
This module centralises the colour palette so the Toga views have a
single source of truth equivalent to ``COLORS`` in ``config.py``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    primary: str
    primary_bg: str
    on_primary: str

    surface: str
    on_surface: str
    subtle: str

    error: str
    success: str
    warning: str

    separator: str

    # Contact / case colours (kept in sync with the Qt version in
    # ``config.py`` so visual parity is preserved where possible).
    anodic: str
    anodic_border: str
    cathodic: str
    cathodic_border: str
    off: str
    off_border: str


LIGHT = Palette(
    primary="#2b63b8",
    primary_bg="#e9f0fb",
    on_primary="#ffffff",
    surface="#ffffff",
    on_surface="#1b1b1b",
    subtle="#6b6b6b",
    error="#c42b2b",
    success="#2a7a3b",
    warning="#b88000",
    separator="#d9d9de",
    anodic="#ff6464",
    anodic_border="#c83232",
    cathodic="#6496ff",
    cathodic_border="#3264c8",
    off="#bebebe",
    off_border="#505050",
)


DARK = Palette(
    primary="#7aa6e8",
    primary_bg="#1e2a3d",
    on_primary="#0d1520",
    surface="#15181d",
    on_surface="#e6e6e6",
    subtle="#a0a0a0",
    error="#ff6464",
    success="#7ed891",
    warning="#ffc857",
    separator="#303338",
    anodic="#ff6464",
    anodic_border="#ff9494",
    cathodic="#6496ff",
    cathodic_border="#94b4ff",
    off="#606060",
    off_border="#909090",
)


def palette(theme: str = "light") -> Palette:
    return DARK if theme.lower() == "dark" else LIGHT
