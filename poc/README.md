# DBS Annotator — Toga PoC

Proof-of-concept that validates the migration of the clinical DBS Annotator
from PySide6/Qt to Toga (BeeWare) across five target platforms: Windows,
Linux, macOS, iOS and Android.

The PoC intentionally exercises the four riskiest areas identified in the
migration plan:

1. **Electrode canvas** — reimplement the custom-painted `ElectrodeCanvas`
   on `toga.Canvas`, including directional segmented contacts, hit testing,
   hover state and PNG export.
2. **Interactive form** — file-save dialog, numeric validation, combo box,
   and a drag-capable scale slider rebuilt on top of `toga.Canvas`.
3. **Async updater** — replace `QThreadPool`/`QRunnable` with `asyncio`
   using `toga.App.add_background_task` / `asyncio.to_thread`.
4. **Report export without docx2pdf/LibreOffice** — generate a DOCX with
   `python-docx` and a PDF with `reportlab`, then open via
   `toga.App.open_url` (which maps to share sheets / document picker on
   mobile).

## Layout

```
poc/
├── pyproject.toml                # Standalone Briefcase project
├── src/
│   └── poc_dbs_annotator/
│       ├── __init__.py
│       ├── __main__.py           # Entry point
│       ├── app.py                # toga.App subclass
│       ├── canvas_electrode.py   # Toga port of ElectrodeCanvas
│       ├── canvas_scale.py       # Canvas-based drag slider (QProgressBar replacement)
│       ├── form_step.py          # Step-1-like form
│       ├── updater.py            # Async GitHub release check
│       ├── exporter.py           # DOCX + ReportLab PDF
│       └── resources/            # PNG assets (pre-rendered from SVGs)
└── README.md                     # This file
```

## Building

```bash
cd poc
uv sync --group build

# Desktop
uv run briefcase dev
uv run briefcase create
uv run briefcase build
uv run briefcase package

# iOS (on macOS)
uv run briefcase create iOS
uv run briefcase build iOS
uv run briefcase run iOS

# Android (any host)
uv run briefcase create android
uv run briefcase build android
uv run briefcase run android
```

## Go/No-Go gates (see the migration plan §7)

Check each of the following on the built PoC:

- [ ] **Canvas fidelity** — Electrode PoC renders acceptably on iOS + Android
  (either with radial-gradient support from the backend, or with the
  fallback linear-gradient approximation in `canvas_electrode.py`).
- [ ] **Export path** — DOCX + PDF both generate on iOS + Android without
  requiring Word/LibreOffice; share sheet opens via `toga.App.open_url`.
- [ ] **Drag latency** — scale slider in `canvas_scale.py` stays smooth at
  60 fps on a low-end Android device.
- [ ] **iOS sandbox** — `toga.SaveFileDialog` completes end-to-end on an
  iOS simulator; files land in the expected document container.

If any gate fails, revisit the migration scope before committing to a full
rewrite of the production app.
