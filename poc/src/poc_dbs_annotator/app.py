"""Toga application shell for the PoC.

Combines the electrode canvas port, the feasibility form, ReportLab export
and the async updater behind a single Toga ``App``. This is the thing that
gets packaged with Briefcase for each of the five targets.
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path

import toga
from toga.style.pack import COLUMN, Pack

from . import __version__
from .exporter import write_docx, write_pdf
from .form_step import FormStep
from .updater import check_async

logger = logging.getLogger(__name__)


class DBSAnnotatorPoC(toga.App):
    def startup(self) -> None:
        main = toga.MainWindow(
            title=f"DBS Annotator PoC v{__version__}",
            size=(1000, 720),
        )

        self.status = toga.Label("Ready.", style=Pack(margin=6, color="#444444"))

        self.form = FormStep(
            on_export_docx=self._write_docx,
            on_export_pdf=self._write_pdf,
            request_save_path=self._save_path,
        )

        layout = toga.Box(style=Pack(direction=COLUMN, flex=1))
        layout.add(self.form)
        layout.add(self.status)
        main.content = layout
        main.show()
        self.main_window = main

        self.on_running = self._background_update_check  # ty: ignore[invalid-assignment]

    # ---- export helpers --------------------------------------------------

    def _render_canvas_to_tmp_png(self) -> Path | None:
        try:
            tmp_dir = Path(tempfile.mkdtemp(prefix="dbs-poc-"))
            png_path = tmp_dir / "electrode.png"
            self.form.canvas.to_png(str(png_path))
            if png_path.exists():
                return png_path
        except Exception as exc:
            logger.warning("Canvas PNG export failed: %s", exc)
        return None

    def _write_docx(self, path: Path, data: dict) -> None:
        png = self._render_canvas_to_tmp_png()
        try:
            out = write_docx(path, data, canvas_png=png)
            self.status.text = f"Saved DOCX: {out}"
            self._share_or_open(out)
        except Exception as exc:
            self.status.text = f"DOCX export failed: {exc}"
            logger.exception("DOCX export failed")

    def _write_pdf(self, path: Path, data: dict) -> None:
        png = self._render_canvas_to_tmp_png()
        try:
            out = write_pdf(path, data, canvas_png=png)
            self.status.text = f"Saved PDF: {out}"
            self._share_or_open(out)
        except Exception as exc:
            self.status.text = f"PDF export failed: {exc}"
            logger.exception("PDF export failed")

    def _share_or_open(self, path: Path) -> None:
        """Open the exported file.

        On desktop this delegates to the OS default handler. On iOS/Android
        Toga routes ``open_url`` through a share sheet / system intent --
        the production migration will wire platform-specific share flows
        here instead of ``os.startfile`` / ``xdg-open`` which don't exist
        on mobile.
        """
        import webbrowser

        try:
            if webbrowser.open(path.resolve().as_uri()):
                return
        except Exception:  # noqa: BLE001
            pass
        try:
            import subprocess
            import sys

            if sys.platform == "win32":
                import os

                os.startfile(str(path))  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])  # noqa: S603
            else:
                subprocess.Popen(["xdg-open", str(path)])  # noqa: S603
        except Exception:  # noqa: BLE001
            logger.info("Could not open exported file; path: %s", path)

    async def _save_path(self, title: str, suggested: str) -> Path | None:
        window = self.main_window
        if not isinstance(window, toga.Window):
            return None
        try:
            result = await window.dialog(
                toga.SaveFileDialog(title=title, suggested_filename=suggested)
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Save dialog failed: %s", exc)
            return None
        if result is None:
            return None
        return Path(str(result))

    # ---- updater ---------------------------------------------------------

    async def _background_update_check(self, *_: object, **__: object) -> None:
        try:
            await asyncio.sleep(1.5)
            info = await check_async(Path(self.paths.data) / "updater_state.json")
            if info:
                self.status.text = (
                    f"Update available: {info.tag_name} -- {info.html_url}"
                )
        except Exception:
            logger.exception("Update check failed")


def main() -> DBSAnnotatorPoC:
    return DBSAnnotatorPoC(
        formal_name="DBSAnnotatorPoC",
        app_id="ch.wysscenter.dbsannotatorpoc",
        app_name="poc_dbs_annotator",
    )


if __name__ == "__main__":
    main().main_loop()
