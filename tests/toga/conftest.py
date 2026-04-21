"""Pytest harness for the Toga backend.

Activates the ``toga-dummy`` backend via the ``TOGA_BACKEND`` environment
variable so a real OS window is never instantiated. A single
``toga.App`` instance is created per test session and the GUI backend is
installed through the Toga bootstrap so
``dbs_annotator.gui.get_*`` works in every test.
"""

from __future__ import annotations

import os

os.environ.setdefault("TOGA_BACKEND", "toga_dummy")

import pytest
import toga

from dbs_annotator.gui.toga_backend.bootstrap import install as install_toga_backend


@pytest.fixture(scope="session")
def toga_app() -> toga.App:
    app = toga.App(
        formal_name="DBSAnnotatorTestHarness",
        app_id="ch.wysscenter.dbsannotator.test",
        app_name="dbs_annotator_test",
    )
    install_toga_backend(app)
    return app


@pytest.fixture(autouse=True)
def _install_gui_backend(toga_app: toga.App):  # noqa: D401
    """Override the root conftest's Qt autouse fixture.

    The root ``tests/conftest.py`` registers the Qt-backed
    :mod:`dbs_annotator.gui` services for every test. For tests under
    ``tests/toga/`` we want the Toga backend instead. pytest's fixture
    resolution prefers the closest definition, so redefining the same
    fixture name here is enough to short-circuit the Qt setup.
    """
    install_toga_backend(toga_app)
    yield
