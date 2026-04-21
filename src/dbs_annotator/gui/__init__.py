"""Thin GUI-backend abstraction.

This package exists so the rest of the app can migrate from PySide6 to
Toga without a big-bang rewrite. It exposes small, backend-neutral
interfaces that the core app depends on; the concrete implementations
live under ``gui.qt`` (Qt/PySide6) today and will gain a sibling
``gui.toga_backend`` during the port (see migration plan Phase 1).

The public surface intentionally mirrors the subset of Qt the app
actually uses -- paths, settings, background execution, the updater
persistence layer, and eventually dialogs. Everything else
(widgets/layouts) is still imported directly from the active backend.
"""

from __future__ import annotations

from .interfaces import (
    BackgroundRunner,
    Clock,
    Paths,
    Settings,
    SettingsProtocol,
    UpdaterStore,
    get_background_runner,
    get_clock,
    get_paths,
    get_settings,
    get_updater_store,
    register_backend,
)

__all__ = [
    "BackgroundRunner",
    "Clock",
    "Paths",
    "Settings",
    "SettingsProtocol",
    "UpdaterStore",
    "get_background_runner",
    "get_clock",
    "get_paths",
    "get_settings",
    "get_updater_store",
    "register_backend",
]
