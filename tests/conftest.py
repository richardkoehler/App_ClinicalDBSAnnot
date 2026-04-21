"""Shared pytest fixtures for Qt and the main wizard."""

from __future__ import annotations

import os

# Headless-friendly Qt before any QWidget is constructed (pytest loads conftest early).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from dbs_annotator.config import FS_APP_NAME, FS_ORG_NAME
from dbs_annotator.gui.interfaces import register_backend
from dbs_annotator.gui.qt.background import QtBackgroundRunner
from dbs_annotator.gui.qt.clock import SystemClock
from dbs_annotator.gui.qt.paths import QtPaths
from dbs_annotator.gui.qt.settings import QtSettings, QtUpdaterStore
from dbs_annotator.views.wizard_window import WizardWindow


@pytest.fixture(autouse=True)
def _install_gui_backend(qapp):
    """Install the Qt-backed :mod:`dbs_annotator.gui` services for every test.

    ``QSettings`` resolves via the ``QApplication`` org/app identity, so the
    identity must be set *before* the Qt backend (and therefore
    ``QtUpdaterStore``) is installed.

    We call ``register_backend`` directly (not ``gui.qt.install``) so the
    Qt services always win, even when the Toga test harness has already
    registered its own implementations earlier in the session.
    """
    if not qapp.applicationName():
        qapp.setApplicationName(FS_APP_NAME)
    if not qapp.organizationName():
        qapp.setOrganizationName(FS_ORG_NAME)
    register_backend(
        paths=QtPaths(),
        settings=QtSettings(),
        background_runner=QtBackgroundRunner(),
        clock=SystemClock(),
        updater_store=QtUpdaterStore(),
    )


@pytest.fixture
def wizard(qtbot, qapp):
    """Main wizard window bound to the session QApplication."""
    w = WizardWindow(qapp)
    qtbot.addWidget(w)
    w.show()
    return w


@pytest.fixture
def bids_like_tsv(tmp_path):
    """Minimal TSV path suitable for SessionData.open_file (new file)."""
    path = tmp_path / "sub-01_ses-20250101_task-prog_run-01_events.tsv"
    path.write_text("", encoding="utf-8")
    return path
