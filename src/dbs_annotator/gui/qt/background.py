"""Qt-backed :class:`dbs_annotator.gui.BackgroundRunner` implementation."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

logger = logging.getLogger(__name__)


class _Signals(QObject):
    success = Signal(object)
    error = Signal(object)


class _Runnable(QRunnable):
    def __init__(
        self,
        func: Callable[..., Any],
        signals: _Signals,
    ) -> None:
        super().__init__()
        self._func = func
        self._signals = signals
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        if self._cancelled:
            return
        try:
            result = self._func()
        except BaseException as exc:
            logger.info("BackgroundRunner task failed: %s", exc)
            self._signals.error.emit(exc)
            return
        if not self._cancelled:
            self._signals.success.emit(result)


class QtBackgroundRunner:
    def submit(
        self,
        func: Callable[..., Any],
        *,
        on_success: Callable[[Any], None] | None = None,
        on_error: Callable[[BaseException], None] | None = None,
    ) -> Callable[[], None]:
        signals = _Signals()
        if on_success is not None:
            signals.success.connect(on_success)
        if on_error is not None:
            signals.error.connect(on_error)
        runnable = _Runnable(func, signals)
        QThreadPool.globalInstance().start(runnable)
        return runnable.cancel
