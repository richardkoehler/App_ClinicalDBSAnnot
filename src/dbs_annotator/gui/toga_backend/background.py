"""Toga-backed :class:`BackgroundRunner` using ``asyncio.to_thread``.

Toga's event loop is an asyncio loop on every backend, so we can run
blocking work off the UI thread without pulling in QThreadPool/QRunnable.
The returned cancel handle flips a flag -- callbacks are suppressed if
the consumer cancels before the worker finishes (best-effort; the thread
itself keeps running to completion).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class TogaBackgroundRunner:
    def submit(
        self,
        func: Callable[..., Any],
        *,
        on_success: Callable[[Any], None] | None = None,
        on_error: Callable[[BaseException], None] | None = None,
    ) -> Callable[[], None]:
        cancelled = {"flag": False}

        async def runner() -> None:
            try:
                result = await asyncio.to_thread(func)
            except BaseException as exc:
                if cancelled["flag"]:
                    return
                logger.info("BackgroundRunner task failed: %s", exc)
                if on_error is not None:
                    on_error(exc)
                return
            if cancelled["flag"]:
                return
            if on_success is not None:
                on_success(result)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.create_task(runner())

        def cancel() -> None:
            cancelled["flag"] = True

        return cancel
