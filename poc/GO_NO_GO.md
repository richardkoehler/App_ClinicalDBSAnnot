# Go/No-Go Review — Toga Migration PoC

Fill this table out **on real devices** before Phase 1 proceeds. The PoC code
in this directory is designed to make each gate mechanically testable.

| # | Gate | Target | How to test | Result |
|---|------|--------|-------------|--------|
| 1 | Canvas fidelity | iOS simulator + Android emulator | `briefcase run iOS` / `briefcase run android`, cycle contacts on `Boston Vercise Cartesia HX`, confirm: ring caps draw in correct position, all 16 segments get state updates, labels are readable. Compare screenshot to `docs/screenshots/electrode_canvas_qt.png`. | ☐ pass ☐ fail |
| 2 | PNG export | iOS + Android | In the PoC, press "Export PDF" → confirm `electrode.png` was embedded (file size > 10 KB, matches canvas visually). | ☐ pass ☐ fail |
| 3 | DOCX + PDF mobile | iOS + Android | Export DOCX then PDF on device. PDF must be produced without calling docx2pdf/LibreOffice (verify via logs). | ☐ pass ☐ fail |
| 4 | Share sheet | iOS + Android | After export, confirm the system share/preview sheet opens (iOS `UIActivityViewController` / Android `ACTION_VIEW`). Allow "Save to Files" / "Save to Drive". | ☐ pass ☐ fail |
| 5 | Drag latency | Low-end Android (e.g. Pixel 3a, 4 GB RAM) | Drag the scale slider for 10 s while recording a 60 fps screen capture. Must stay ≥ 55 fps. Use `adb shell dumpsys gfxinfo` before/after. | ☐ pass ☐ fail |
| 6 | iOS sandbox file-save | iOS simulator | Export DOCX with the save dialog; confirm the file actually lands in the app's Documents/ container and is readable back. | ☐ pass ☐ fail |
| 7 | Desktop parity | Windows + macOS + Linux | Run `briefcase dev`, confirm all widgets render, drag-and-click still works, DOCX + PDF open in the default handler. | ☐ pass ☐ fail |
| 8 | No PySide6 in mobile wheels | iOS + Android | `python scripts/verify_no_pyside6.py build` must exit 0. | ☐ pass ☐ fail |

## Decision rule

Proceed to Phase 1 (full migration) only if **all** of gates 1–8 pass.

If any gate fails, document the failure mode below and re-scope before
committing more engineering time. The likely fallbacks are:

* **Canvas fidelity fail**: accept flat-shaded contacts on mobile;
  ship radial-gradient variant only on desktop (cheap; already
  controlled by `use_gradients` in `canvas_electrode.py`).
* **PDF export fail on mobile**: switch from ReportLab to `fpdf2`, or
  generate DOCX only on mobile and defer PDF to a desktop
  companion.
* **Drag latency fail**: reduce canvas complexity (dirty-region
  caching; bake base lead into a pre-rendered `toga.Image` and redraw
  only contact overlays — noted in migration plan §9).
* **iOS sandbox fail**: switch to `toga.App.paths.documents` and provide
  an in-app file browser instead of the system document picker.

## Notes

- The go/no-go gates 1–7 require *physical* devices or the appropriate
  simulator/emulator; they cannot be validated from the codebase alone.
  The PoC is structured so they can be exercised in ~1 day of testing
  once the environments are set up.
- Gate 8 is automatable — it runs on every push via
  `.github/workflows/poc-toga.yml`.
