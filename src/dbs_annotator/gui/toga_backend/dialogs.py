"""Thin async helpers around Toga's native dialog primitives.

The Qt app uses ``QMessageBox.warning``/``information``/``question`` and
``QFileDialog``. Toga exposes equivalent primitives on
``toga.Window.dialog(...)``; the helpers below absorb the (minor) API
churn between Toga 0.4 and 0.5 so the views stay tidy.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import toga


async def _dispatch(window: toga.Window, dlg: Any) -> Any:
    try:
        return await window.dialog(dlg)
    except AttributeError:
        return await dlg


async def info(window: toga.Window, title: str, message: str) -> None:
    await _dispatch(window, toga.InfoDialog(title, message))


async def warn(window: toga.Window, title: str, message: str) -> None:
    try:
        dlg = toga.ErrorDialog(title, message)
    except AttributeError:
        dlg = toga.InfoDialog(title, message)
    await _dispatch(window, dlg)


async def error(window: toga.Window, title: str, message: str) -> None:
    try:
        dlg = toga.ErrorDialog(title, message)
    except AttributeError:
        dlg = toga.InfoDialog(title, message)
    await _dispatch(window, dlg)


async def confirm(window: toga.Window, title: str, message: str) -> bool:
    try:
        dlg = toga.ConfirmDialog(title, message)
    except AttributeError:
        dlg = toga.QuestionDialog(title, message)
    result = await _dispatch(window, dlg)
    return bool(result)


async def ask_text(
    window: toga.Window, title: str, message: str, default: str = ""
) -> str | None:
    """Request a single-line text input. Returns ``None`` on cancel."""
    factory = getattr(toga, "TextInputDialog", None)
    if factory is None:
        # Fallback: no prompt dialog available -> accept default.
        return default
    dlg = factory(title, message, initial=default)
    result = await _dispatch(window, dlg)
    if result is None:
        return None
    return str(result)


async def save_file(
    window: toga.Window,
    title: str,
    suggested_name: str,
    file_types: Iterable[str] | None = None,
) -> Path | None:
    types = list(file_types) if file_types else None
    try:
        dlg = toga.SaveFileDialog(
            title, suggested_filename=suggested_name, file_types=types
        )
    except TypeError:
        dlg = toga.SaveFileDialog(title, suggested_name, types)
    result = await _dispatch(window, dlg)
    if result is None:
        return None
    return Path(str(result))


async def open_file(
    window: toga.Window,
    title: str,
    file_types: Iterable[str] | None = None,
) -> Path | None:
    types = list(file_types) if file_types else None
    dlg = toga.OpenFileDialog(title, file_types=types)
    result = await _dispatch(window, dlg)
    if result is None:
        return None
    return Path(str(result))


async def open_multi_file(
    window: toga.Window,
    title: str,
    file_types: Iterable[str] | None = None,
) -> list[Path]:
    types = list(file_types) if file_types else None
    dlg = toga.OpenFileDialog(title, file_types=types, multiple_select=True)
    result = await _dispatch(window, dlg)
    if not result:
        return []
    if isinstance(result, list):
        return [Path(str(p)) for p in result]
    return [Path(str(result))]
