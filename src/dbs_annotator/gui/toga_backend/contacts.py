"""Backend-neutral helpers for electrode contact/anode/cathode tokens.

Ports ``get_cathode_labels`` and the token-string encoders from the Qt
``Step1View`` without pulling PySide6 in.
"""

from __future__ import annotations

from ...config_electrode_models import ContactState


def get_cathode_labels(canvas) -> list[str]:
    """Ordered cathode contact labels ("E1b", "E2a", ...). Case included."""
    model = getattr(canvas, "model", None)
    if not model:
        return []

    labels: list[str] = []

    if canvas.case_state == ContactState.CATHODIC:
        labels.append("case")

    if model.is_directional:
        for contact_idx in range(model.num_contacts):
            if model.is_level_directional(contact_idx):
                seg_states = [
                    canvas.contact_states.get((contact_idx, seg), ContactState.OFF)
                    for seg in range(3)
                ]
                if all(s == ContactState.CATHODIC for s in seg_states):
                    labels.append(f"E{contact_idx}")
                    continue
                seg_labels = ["a", "b", "c"]
                for seg, seg_state in enumerate(seg_states):
                    if seg_state == ContactState.CATHODIC:
                        labels.append(f"E{contact_idx}{seg_labels[seg]}")
            else:
                state = canvas.contact_states.get((contact_idx, 0), ContactState.OFF)
                if state == ContactState.CATHODIC:
                    labels.append(f"E{contact_idx}")
    else:
        for contact_idx in range(model.num_contacts):
            state = canvas.contact_states.get((contact_idx, 0), ContactState.OFF)
            if state == ContactState.CATHODIC:
                labels.append(f"E{contact_idx}")

    return labels


def anode_cathode_tokens(canvas) -> tuple[str, str]:
    """``(anode_tokens, cathode_tokens)`` joined with ``_``."""
    model = getattr(canvas, "model", None)
    if not model:
        return "", ""

    anodes: list[str] = []
    cathodes: list[str] = []

    if canvas.case_state == ContactState.ANODIC:
        anodes.append("case")
    elif canvas.case_state == ContactState.CATHODIC:
        cathodes.append("case")

    if model.is_directional:
        for contact_idx in range(model.num_contacts):
            if model.is_level_directional(contact_idx):
                seg_states = [
                    canvas.contact_states.get((contact_idx, seg), ContactState.OFF)
                    for seg in range(3)
                ]
                if all(s == ContactState.ANODIC for s in seg_states):
                    anodes.append(f"E{contact_idx}")
                    continue
                if all(s == ContactState.CATHODIC for s in seg_states):
                    cathodes.append(f"E{contact_idx}")
                    continue
                seg_labels = ["a", "b", "c"]
                for seg, seg_state in enumerate(seg_states):
                    if seg_state == ContactState.ANODIC:
                        anodes.append(f"E{contact_idx}{seg_labels[seg]}")
                    elif seg_state == ContactState.CATHODIC:
                        cathodes.append(f"E{contact_idx}{seg_labels[seg]}")
            else:
                state = canvas.contact_states.get((contact_idx, 0), ContactState.OFF)
                if state == ContactState.ANODIC:
                    anodes.append(f"E{contact_idx}")
                elif state == ContactState.CATHODIC:
                    cathodes.append(f"E{contact_idx}")
    else:
        for contact_idx in range(model.num_contacts):
            state = canvas.contact_states.get((contact_idx, 0), ContactState.OFF)
            if state == ContactState.ANODIC:
                anodes.append(f"E{contact_idx}")
            elif state == ContactState.CATHODIC:
                cathodes.append(f"E{contact_idx}")

    return "_".join(anodes), "_".join(cathodes)


def apply_tokens_to_canvas(canvas, anode_text: str, cathode_text: str) -> None:
    """Inverse of :func:`anode_cathode_tokens` — set canvas contact states."""
    model = getattr(canvas, "model", None)
    if not model:
        return

    canvas.contact_states.clear()
    canvas.case_state = ContactState.OFF

    def apply(text: str, state: int) -> None:
        if not text:
            return
        for raw in text.split("_"):
            token = raw.strip()
            if not token:
                continue
            if token == "case":
                canvas.case_state = state
                continue
            if token.startswith("E") and len(token) >= 2:
                try:
                    if token[-1].isalpha():
                        idx = int(token[1:-1])
                        seg = {"a": 0, "b": 1, "c": 2}.get(token[-1].lower())
                        if seg is not None:
                            canvas.contact_states[(idx, seg)] = state
                    else:
                        idx = int(token[1:])
                        if model.is_directional:
                            for seg in range(3):
                                canvas.contact_states[(idx, seg)] = state
                        else:
                            canvas.contact_states[(idx, 0)] = state
                except ValueError:
                    continue

    apply(anode_text, ContactState.ANODIC)
    apply(cathode_text, ContactState.CATHODIC)
    if hasattr(canvas, "_repaint"):
        canvas._repaint()
