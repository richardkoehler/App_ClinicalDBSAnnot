"""Icon / SVG resource helpers for the Toga build.

Toga's ``Icon`` accepts PNGs on every backend but SVG support is
inconsistent (notably broken on Android). This helper pre-renders SVGs
to PNG on demand, caching the result in the app's cache directory so
subsequent launches are zero-cost.

Also exposes a lazy-import shim for ``pandas`` / ``matplotlib`` so
mobile cold-start stays fast: nothing pulls them in unless a report
view is opened.
"""

from __future__ import annotations

import hashlib
import importlib
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def svg_to_png(svg_path: Path, cache_dir: Path, *, size: int = 128) -> Path:
    """Return a PNG rendering of ``svg_path``, rendered on demand.

    Requires Pillow + CairoSVG on Linux/macOS/Windows/iOS/Android. The
    cache key is ``sha256(svg_bytes) || size``.
    """
    svg_bytes = svg_path.read_bytes()
    digest = hashlib.sha256(svg_bytes).hexdigest()[:16]
    cache_dir.mkdir(parents=True, exist_ok=True)
    out = cache_dir / f"{svg_path.stem}-{digest}-{size}.png"
    if out.exists():
        return out

    try:
        import cairosvg
    except ImportError as exc:
        raise RuntimeError(
            "svg_to_png requires cairosvg (pip install cairosvg)"
        ) from exc

    cairosvg.svg2png(
        bytestring=svg_bytes, write_to=str(out), output_width=size, output_height=size
    )
    return out


_lazy_cache: dict[str, Any] = {}


def lazy_import(name: str) -> Any:
    """Import ``name`` on first call only.

    Used to keep ``pandas`` / ``matplotlib`` out of the mobile cold-start
    path. On desktop the two-pass import costs ~0ms; on Android it saves
    several hundred milliseconds on launch.
    """
    mod = _lazy_cache.get(name)
    if mod is None:
        logger.debug("Lazy-importing %s", name)
        mod = importlib.import_module(name)
        _lazy_cache[name] = mod
    return mod
