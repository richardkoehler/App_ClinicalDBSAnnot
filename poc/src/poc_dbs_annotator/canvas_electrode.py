"""Toga re-implementation of ``ElectrodeCanvas``.

This PoC demonstrates that the Qt-painted electrode widget (see
``src/dbs_annotator/models/electrode_viewer.py`` in the main app) can be
rebuilt on top of ``toga.Canvas`` while keeping:

* the visual structure (case, lead body, ring contacts, directional
  segments, ring cap, contact labels);
* cycle-on-click state machine (OFF → ANODIC → CATHODIC → OFF);
* ring-level bulk toggling;
* hover tracking;
* PNG export via ``canvas.as_image()``.

Platform notes:

* Radial gradients are not universally supported across Toga backends
  (OK on Cocoa/GTK/Winforms, missing on iOS/Android at time of writing).
  The canvas therefore paints flat-shaded contacts by default and uses
  an optional linear-gradient highlight when ``use_gradients`` is True
  and the backend supports it.
* ``QPainterPathStroker`` has no Toga equivalent; expanded hit areas are
  computed as padded bounding boxes on the CPU side (good enough for
  touch targets and keeps the code backend-independent).
"""

from __future__ import annotations

from collections.abc import Callable

import toga
from toga.colors import Color, rgb, rgba
from toga.style.pack import Pack

from .electrode_models import ContactState, ElectrodeModel, validate_configuration

# ---------- colour helpers --------------------------------------------------

ANODIC_BASE = rgb(255, 100, 100)
ANODIC_BORDER = rgb(200, 50, 50)
CATHODIC_BASE = rgb(100, 150, 255)
CATHODIC_BORDER = rgb(50, 100, 200)
OFF_BASE = rgb(190, 190, 190)
OFF_BORDER = rgb(80, 80, 80)

LEAD_FILL = rgb(220, 220, 225)
LEAD_STROKE = rgb(150, 150, 160)
LABEL_BLACK = rgb(20, 20, 20)
LABEL_WHITE = rgb(250, 250, 250)
SHADOW = rgba(0, 0, 0, 0.18)
HIGHLIGHT = rgba(255, 255, 255, 0.22)


def _lighten(c: Color, amount: float) -> Color:
    c_rgb: rgb = c.rgb  # ty: ignore[unresolved-attribute]
    r, g, b = c_rgb.r, c_rgb.g, c_rgb.b
    return rgb(
        min(255, int(r + (255 - r) * amount)),
        min(255, int(g + (255 - g) * amount)),
        min(255, int(b + (255 - b) * amount)),
    )


def _darken(c: Color, amount: float) -> Color:
    c_rgb: rgb = c.rgb  # ty: ignore[unresolved-attribute]
    r, g, b = c_rgb.r, c_rgb.g, c_rgb.b
    return rgb(int(r * (1 - amount)), int(g * (1 - amount)), int(b * (1 - amount)))


def _state_colors(state: int, hovered: bool) -> tuple[Color, Color, float]:
    if state == ContactState.ANODIC:
        base, border = ANODIC_BASE, ANODIC_BORDER
    elif state == ContactState.CATHODIC:
        base, border = CATHODIC_BASE, CATHODIC_BORDER
    else:
        base, border = OFF_BASE, OFF_BORDER
    if hovered:
        base = _lighten(base, 0.12)
        border = _lighten(border, 0.12)
    width = 3.0 if state != ContactState.OFF else 1.0
    if hovered:
        width += 1.0
    return base, border, width


# ---------- geometry helpers ------------------------------------------------


def _point_in_polygon(px: float, py: float, poly: list[tuple[float, float]]) -> bool:
    """Ray-cast polygon containment test (no numpy, works on iOS/Android)."""
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > py) != (yj > py)) and (
            px < (xj - xi) * (py - yi) / (yj - yi + 1e-9) + xi
        ):
            inside = not inside
        j = i
    return inside


def _point_in_rect(
    px: float,
    py: float,
    rect: tuple[float, float, float, float],
    pad: float = 0.0,
) -> bool:
    x, y, w, h = rect
    return (x - pad) <= px <= (x + w + pad) and (y - pad) <= py <= (y + h + pad)


# ---------- main widget -----------------------------------------------------


class ElectrodeCanvas(toga.Box):
    """A single electrode viewer using a toga.Canvas for drawing."""

    def __init__(
        self,
        model: ElectrodeModel | None = None,
        *,
        export_mode: bool = False,
        on_validation: Callable[[bool, str], None] | None = None,
        use_gradients: bool = True,
        width: int = 260,
        height: int = 560,
    ) -> None:
        super().__init__(style=Pack(width=width, height=height))
        self._w = width
        self._h = height
        self.model: ElectrodeModel | None = model
        self.export_mode = export_mode
        self.use_gradients = use_gradients
        self.on_validation = on_validation

        self.contact_states: dict[tuple[int, int], int] = {}
        self.case_state: int = ContactState.OFF

        # Hit-test caches (rebuilt every paint)
        self._contact_polys: dict[tuple[int, int], list[tuple[float, float]]] = {}
        self._contact_rects: dict[
            tuple[int, int], tuple[float, float, float, float]
        ] = {}
        self._ring_rects: dict[int, tuple[float, float, float, float]] = {}
        self._case_rect: tuple[float, float, float, float] | None = None

        self.hovered_contact: tuple[int, int] | None = None
        self.hovered_ring: int | None = None
        self.hovered_case: bool = False

        self.canvas = toga.Canvas(
            style=Pack(flex=1, width=width, height=height),
            on_press=self._on_press,
            on_drag=self._on_drag,
            on_release=self._on_release,
            on_resize=self._on_resize,
        )
        self.add(self.canvas)
        self._repaint()

    # ---- public API ----

    def set_model(self, model: ElectrodeModel | None) -> None:
        self.model = model
        self.contact_states.clear()
        self.case_state = ContactState.OFF
        self._repaint()

    def set_export_mode(self, enabled: bool) -> None:
        self.export_mode = enabled
        self._repaint()

    def to_png(self, path: str) -> str:
        """Render the current canvas to a PNG file via Pillow."""
        img = self.canvas.as_image()
        img.save(path)
        return path

    # ---- input handling ----

    def _on_resize(self, widget, width: int, height: int, **_: object) -> None:
        self._w = max(1, int(width))
        self._h = max(1, int(height))
        self._repaint()

    def _on_press(self, widget, x: float, y: float, **_: object) -> None:
        hit_contact = self._hit_contact(x, y)
        if hit_contact is not None:
            self._cycle_contact(hit_contact)
            return
        hit_ring = self._hit_ring(x, y)
        if hit_ring is not None:
            self._cycle_ring(hit_ring)
            return
        if self._case_rect and _point_in_rect(x, y, self._case_rect, pad=4):
            self._cycle_case()

    def _on_drag(self, widget, x: float, y: float, **_: object) -> None:
        new_contact = self._hit_contact(x, y)
        new_ring = self._hit_ring(x, y)
        new_case = bool(
            self._case_rect and _point_in_rect(x, y, self._case_rect, pad=4)
        )
        if (
            new_contact != self.hovered_contact
            or new_ring != self.hovered_ring
            or new_case != self.hovered_case
        ):
            self.hovered_contact = new_contact
            self.hovered_ring = new_ring
            self.hovered_case = new_case
            self._repaint()

    def _on_release(self, widget, x: float, y: float, **_: object) -> None:
        pass

    # ---- state transitions ----

    def _cycle_contact(self, cid: tuple[int, int]) -> None:
        new = dict(self.contact_states)
        cur = new.get(cid, ContactState.OFF)
        if cur == ContactState.OFF:
            new[cid] = ContactState.ANODIC
        elif cur == ContactState.ANODIC:
            new[cid] = ContactState.CATHODIC
        else:
            new.pop(cid, None)
        self._apply(new, self.case_state)

    def _cycle_case(self) -> None:
        nxt = {
            ContactState.OFF: ContactState.ANODIC,
            ContactState.ANODIC: ContactState.CATHODIC,
            ContactState.CATHODIC: ContactState.OFF,
        }[self.case_state]
        self._apply(dict(self.contact_states), nxt)

    def _cycle_ring(self, ring_idx: int) -> None:
        if not self.model or not self.model.is_directional:
            return
        states = [
            self.contact_states.get((ring_idx, seg), ContactState.OFF)
            for seg in range(3)
        ]
        if all(s == ContactState.OFF for s in states):
            target = ContactState.ANODIC
        elif all(s == ContactState.ANODIC for s in states):
            target = ContactState.CATHODIC
        else:
            target = ContactState.OFF
        new = dict(self.contact_states)
        for seg in range(3):
            cid = (ring_idx, seg)
            if target == ContactState.OFF:
                new.pop(cid, None)
            else:
                new[cid] = target
        self._apply(new, self.case_state)

    def _apply(self, states: dict, case_state: int) -> None:
        ok, msg = validate_configuration(states, case_state)
        self.contact_states = states
        self.case_state = case_state
        if self.on_validation is not None:
            self.on_validation(ok, msg)
        self._repaint()

    # ---- hit testing ----

    def _hit_contact(self, x: float, y: float) -> tuple[int, int] | None:
        for cid, poly in self._contact_polys.items():
            if _point_in_polygon(x, y, poly):
                return cid
        for cid, rect in self._contact_rects.items():
            if _point_in_rect(x, y, rect, pad=6):
                return cid
        return None

    def _hit_ring(self, x: float, y: float) -> int | None:
        for rid, rect in self._ring_rects.items():
            if _point_in_rect(x, y, rect, pad=6):
                return rid
        return None

    # ---- drawing ----

    def _calc_scale(self) -> float:
        if not self.model:
            return 20.0
        contacts_mm = (
            self.model.num_contacts * self.model.contact_height
            + max(0, self.model.num_contacts - 1) * self.model.contact_spacing
        )
        top_padding = 2 if self.export_mode else 7
        lead_gap = 8 if self.export_mode else 15
        fixed_px = top_padding + lead_gap
        scale_overhead = 4.0 + 2.0 + max(0, self.model.num_contacts - 1) * 1.0 + 0.3
        usable = max(1, self._h - fixed_px - 2)
        s = usable / (contacts_mm + scale_overhead)
        cap = 80.0 if self.export_mode else 24.0
        return min(s, cap)

    def _repaint(self) -> None:
        ctx = self.canvas.context
        ctx.clear()
        self._contact_polys.clear()
        self._contact_rects.clear()
        self._ring_rects.clear()
        self._case_rect = None

        if self.model is None:
            return

        scale = self._calc_scale()
        center_x = self._w / 2 - 4
        top_padding = 2 if self.export_mode else 7

        # --- case ---
        case_h = 4 * scale
        case_w = self.model.lead_diameter * scale * 1.35 + 10
        case_x = center_x - case_w / 2
        case_y = top_padding
        self._case_rect = (case_x, case_y, case_w, case_h)

        c_base, c_border, c_width = _state_colors(self.case_state, self.hovered_case)
        with ctx.Fill(color=c_base) as fill:
            fill.rect(case_x, case_y, case_w, case_h)
        with ctx.Stroke(color=c_border, line_width=c_width) as stroke:
            stroke.rect(case_x, case_y, case_w, case_h)

        case_text_color = (
            LABEL_WHITE if self.case_state != ContactState.OFF else LABEL_BLACK
        )
        with ctx.Fill(color=case_text_color) as label_fill:
            label_fill.write_text(
                "CASE",
                case_x + case_w / 2 - 14 * (scale / 24),
                case_y + case_h / 2 + 4,
                font=toga.Font(
                    family="sans-serif",
                    size=max(7, int(scale * 0.3)),
                ),
            )

        # --- lead body ---
        lead_w = self.model.lead_diameter * scale * 1.8
        start_y = case_y + case_h + (8 if self.export_mode else 15)
        contact_h_px = self.model.contact_height * scale
        e0_y = start_y + 2 * scale
        for _ in range(self.model.num_contacts - 1):
            e0_y += contact_h_px + (self.model.contact_spacing + 1.0) * scale
        if self.model.tip_contact:
            total_h = e0_y - start_y
        else:
            total_h = e0_y + contact_h_px + 0.3 * scale - start_y

        with ctx.Fill(color=LEAD_FILL) as fill:
            fill.rect(center_x - lead_w / 2, start_y, lead_w, total_h)
        with ctx.Stroke(color=LEAD_STROKE, line_width=2) as stroke:
            stroke.rect(center_x - lead_w / 2, start_y, lead_w, total_h)

        # --- contacts ---
        current_y = start_y + 2 * scale
        base_extension = lead_w * 0.22 if self.model.is_directional else 0

        for i in range(self.model.num_contacts):
            contact_idx = self.model.num_contacts - 1 - i
            is_dir = self.model.is_level_directional(contact_idx)

            if is_dir:
                self._draw_directional_level(
                    ctx,
                    contact_idx,
                    center_x,
                    lead_w,
                    base_extension,
                    current_y,
                    contact_h_px,
                    scale,
                )
            else:
                self._draw_ring_contact(
                    ctx,
                    contact_idx,
                    center_x,
                    lead_w,
                    current_y,
                    contact_h_px,
                    scale,
                )

            # left-side "E0", "E1" label
            label = f"E{contact_idx}"
            with ctx.Fill(color=LABEL_BLACK) as label_fill:
                label_fill.write_text(
                    label,
                    center_x - lead_w / 2 - 26,
                    current_y + contact_h_px / 2 + 4,
                    font=toga.Font(family="sans-serif", size=max(8, int(scale * 0.4))),
                )

            current_y += contact_h_px + (self.model.contact_spacing + 1.0) * scale

        self.canvas.redraw()

    def _draw_ring_contact(
        self,
        ctx,
        contact_idx: int,
        center_x: float,
        lead_w: float,
        current_y: float,
        contact_h_px: float,
        scale: float,
    ) -> None:
        cid = (contact_idx, 0)
        state = self.contact_states.get(cid, ContactState.OFF)
        hovered = self.hovered_contact == cid
        base, border, width = _state_colors(state, hovered)

        rect = (
            center_x - lead_w / 2 + 2,
            current_y,
            lead_w - 4,
            contact_h_px,
        )
        self._contact_rects[cid] = rect

        with ctx.Fill(color=base) as fill:
            fill.rect(*rect)
        with ctx.Stroke(color=border, line_width=width) as stroke:
            stroke.rect(*rect)

        if state != ContactState.OFF:
            hl = (rect[0] + rect[2] * 0.15, rect[1] + 2, rect[2] * 0.3, rect[3] * 0.35)
            with ctx.Fill(color=HIGHLIGHT) as fill:
                fill.rect(*hl)

    def _draw_directional_level(
        self,
        ctx,
        contact_idx: int,
        center_x: float,
        lead_w: float,
        extension: float,
        current_y: float,
        contact_h_px: float,
        scale: float,
    ) -> None:
        b_width = lead_w * 0.55
        b_left = center_x - b_width / 2
        x_left = center_x - lead_w / 2 - extension
        x_right = center_x + lead_w / 2 + extension

        # segment a (left)
        poly_a = [
            (x_left - 2, current_y),
            (b_left - 1, current_y),
            (b_left - 2, current_y + contact_h_px),
            (x_left + extension / 2, current_y + contact_h_px),
        ]
        self._draw_segment(ctx, (contact_idx, 0), poly_a, "a", scale)

        # segment b (centre)
        rect_b = (b_left, current_y, b_width, contact_h_px)
        poly_b = [
            (rect_b[0], rect_b[1]),
            (rect_b[0] + rect_b[2], rect_b[1]),
            (rect_b[0] + rect_b[2], rect_b[1] + rect_b[3]),
            (rect_b[0], rect_b[1] + rect_b[3]),
        ]
        self._draw_segment(ctx, (contact_idx, 1), poly_b, "b", scale)

        # segment c (right)
        poly_c = [
            (b_left + b_width + 2, current_y),
            (x_right + 2, current_y),
            (x_right - extension / 2, current_y + contact_h_px),
            (b_left + b_width + 2, current_y + contact_h_px),
        ]
        self._draw_segment(ctx, (contact_idx, 2), poly_c, "c", scale)

        # ring cap (allows bulk toggle)
        ring_rect = (
            x_left,
            current_y - contact_h_px * 0.6,
            x_right - x_left,
            contact_h_px * 0.5,
        )
        self._ring_rects[contact_idx] = ring_rect

        ring_states = [
            self.contact_states.get((contact_idx, s), ContactState.OFF)
            for s in range(3)
        ]
        if all(s == ContactState.ANODIC for s in ring_states):
            ring_state = ContactState.ANODIC
        elif all(s == ContactState.CATHODIC for s in ring_states):
            ring_state = ContactState.CATHODIC
        else:
            ring_state = ContactState.OFF
        base, border, width = _state_colors(
            ring_state, self.hovered_ring == contact_idx
        )
        with ctx.Fill(color=base) as fill:
            fill.rect(*ring_rect)
        with ctx.Stroke(color=border, line_width=width) as stroke:
            stroke.rect(*ring_rect)
        ring_text_color = LABEL_WHITE if ring_state != ContactState.OFF else LABEL_BLACK
        with ctx.Fill(color=ring_text_color) as ring_fill:
            ring_fill.write_text(
                "Ring",
                ring_rect[0] + ring_rect[2] / 2 - 12,
                ring_rect[1] + ring_rect[3] / 2 + 4,
                font=toga.Font(family="sans-serif", size=max(6, int(scale * 0.28))),
            )

    def _draw_segment(
        self,
        ctx,
        cid: tuple[int, int],
        poly: list[tuple[float, float]],
        label: str,
        scale: float,
    ) -> None:
        state = self.contact_states.get(cid, ContactState.OFF)
        hovered = self.hovered_contact == cid
        base, border, width = _state_colors(state, hovered)

        self._contact_polys[cid] = poly
        # Also record a bounding box for touch-friendly hit expansion
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        self._contact_rects[cid] = (
            min(xs),
            min(ys),
            max(xs) - min(xs),
            max(ys) - min(ys),
        )

        with ctx.Fill(color=base) as fill:
            fill.move_to(*poly[0])
            for p in poly[1:]:
                fill.line_to(*p)
            fill.close_path()
        with ctx.Stroke(color=border, line_width=width) as stroke:
            stroke.move_to(*poly[0])
            for p in poly[1:]:
                stroke.line_to(*p)
            stroke.close_path()

        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)
        seg_text_color = LABEL_WHITE if state != ContactState.OFF else LABEL_BLACK
        with ctx.Fill(color=seg_text_color) as seg_fill:
            seg_fill.write_text(
                label,
                cx - 3,
                cy + 4,
                font=toga.Font(family="sans-serif", size=max(7, int(scale * 0.4))),
            )
