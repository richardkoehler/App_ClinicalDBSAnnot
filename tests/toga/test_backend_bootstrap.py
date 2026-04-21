"""Smoke tests for the Toga backend installation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from dbs_annotator.gui import (
    get_background_runner,
    get_clock,
    get_paths,
    get_settings,
    get_updater_store,
)


def test_paths_returns_writable_dir(toga_app):
    path = get_paths().user_data_dir()
    assert path.exists() and path.is_dir()


def test_settings_roundtrip(toga_app):
    settings = get_settings()
    settings.set("my_key", "my_value")
    assert settings.get("my_key") == "my_value"
    assert settings.get("missing", "default") == "default"


def test_updater_store_records_and_reads_last_check(toga_app):
    store = get_updater_store()
    now = datetime.now(UTC)
    store.record_check(now)
    last = store.last_check()
    assert last is not None
    assert abs((last - now).total_seconds()) < 1


def test_updater_store_cooldown_elapsed_initially(toga_app, tmp_path, monkeypatch):
    from dbs_annotator.gui.toga_backend.settings import TogaUpdaterStore

    store = TogaUpdaterStore(tmp_path)
    assert store.cooldown_elapsed(timedelta(hours=24), datetime.now(UTC)) is True


def test_clock_now_is_tz_aware(toga_app):
    now = get_clock().now()
    assert now.tzinfo is not None


def test_background_runner_is_registered(toga_app):
    assert get_background_runner() is not None
