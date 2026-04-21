"""Click-to-browse file chooser replacing the Qt ``FileDropLineEdit``.

Toga has no public drag-and-drop API today, so the desktop drop affordance
is replaced with a click-to-browse button. The UX is identical on mobile
where drag-and-drop never existed.

The caller supplies ``window`` (needed to anchor the async dialog) and a
callback ``on_file_selected(Path)``. We store the last path in the box's
``value`` property for parity with the Qt widget.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

import toga
from toga.style.pack import ROW, Pack


class FileChooser(toga.Box):
    def __init__(
        self,
        *,
        window: toga.Window,
        title: str = "Open file",
        placeholder: str = "No file selected",
        file_types: Iterable[str] | None = None,
        on_file_selected: Callable[[Path], None] | None = None,
    ) -> None:
        super().__init__(style=Pack(direction=ROW, flex=1))
        self._dialog_host = window
        self._title = title
        self._file_types = list(file_types) if file_types else None
        self._on_file_selected = on_file_selected
        self._path: Path | None = None

        self.display = toga.TextInput(
            placeholder=placeholder, readonly=True, style=Pack(flex=1)
        )
        self.browse = toga.Button("Browse...", on_press=self._on_browse)
        self.add(self.display)
        self.add(self.browse)

    @property
    def value(self) -> Path | None:
        return self._path

    def set_value(self, path: Path | str | None) -> None:
        self._path = Path(path) if path is not None else None
        self.display.value = str(self._path) if self._path else ""

    async def _on_browse(self, widget) -> None:
        try:
            result = await self._dialog_host.open_file_dialog(
                title=self._title, file_types=self._file_types
            )
        except AttributeError:
            # Older Toga versions expose the dialog differently.
            result = await self._dialog_host.dialog(
                toga.OpenFileDialog(title=self._title, file_types=self._file_types)
            )
        if result is None:
            return
        path = Path(str(result))
        self.set_value(path)
        if self._on_file_selected is not None:
            self._on_file_selected(path)
