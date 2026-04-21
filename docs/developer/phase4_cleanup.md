# Phase 4 — PySide6 removal checklist

Phase 4 removes the Qt runtime dependency entirely. **Do not start
this phase until Phase 2 is complete** -- every Qt view in
`src/dbs_annotator/views/` and `src/dbs_annotator/ui/` must have a
working Toga port with unit tests under `tests/toga/`.

## Entry gate (blocks the start of Phase 4)

- [ ] All files in `src/dbs_annotator/views/` have a Toga counterpart
  under `src/dbs_annotator/gui/toga_backend/views/`.
- [ ] `src/dbs_annotator/ui/*` ported (file dialogs, custom widgets).
- [ ] Wizard controller exercises the Toga backend end-to-end for at
  least one full annotation session on Windows, macOS and Linux.
- [ ] `poc/GO_NO_GO.md` gates 1--4 all marked **PASS** on the
  target devices.
- [ ] A Toga build has been exercised on iOS simulator + Android
  emulator via Briefcase (manual or CI).

## Removal steps

1. **Delete the Qt backend:**
   - `src/dbs_annotator/gui/qt/` folder
   - `src/dbs_annotator/__main__.py` (Qt bootstrap) -- replace with a
     thin shim that calls `gui.toga_backend.app.main()`
   - `src/dbs_annotator/styles/` (QSS)
   - `src/dbs_annotator/views/` and `src/dbs_annotator/ui/` (Qt-only)
   - `src/dbs_annotator/utils/theme_manager.py` (QSS loader)

2. **Trim dependencies in `pyproject.toml`:**
   - Remove `pyside6` from `[project].dependencies`.
   - Move `docx2pdf` out of the core deps; it becomes optional and is
     only pulled in by the legacy Windows Word integration if we keep
     it.
   - Promote `toga` to a core dependency and drop the `[toga]` extra.
   - Remove `pyside6-stubs` from `[dependency-groups].dev`.

3. **Replace the test harness:**
   - Delete `pytest-qt` from `[dependency-groups].dev`.
   - Remove `tests/unit/*` tests that hard-depend on `QWidget` /
     `QApplication` and re-home any pure-domain tests to
     `tests/unit/domain/`.
   - The `_install_gui_backend` autouse fixture in `tests/conftest.py`
     is replaced by the Toga version currently in
     `tests/toga/conftest.py`.

4. **CI / packaging:**
   - Drop the Qt-specific installers from `release.yml` (Windows MSI /
     macOS DMG are rebuilt via the Toga targets).
   - Add iOS / Android packaging steps using the keystore / provisioning
     profile secrets described in `docs/developer/mobile_build.md`.
   - Verify `scripts/verify_no_pyside6.py` runs clean against every
     Briefcase artefact before release.

5. **Docs:**
   - Remove the "GUI stack is PySide6 (Qt)" references from
     `README.md` and the user-facing docs.
   - Delete `docs/developer/toga_migration.md` -- replace with a short
     "Design" note covering the Toga architecture.
   - Update `CHANGELOG.md` with the platform expansion.

## Rollback plan

Tag the commit that lands the Toga-only build as
`vX.Y.0-togakickoff`. If a blocker surfaces post-merge, revert to the
previous tag and re-open Phase 2 with the specific failure documented
in a new `poc/GO_NO_GO.md`-style gate entry.
