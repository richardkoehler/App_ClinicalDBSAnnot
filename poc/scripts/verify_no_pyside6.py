"""Walk a Briefcase build tree and fail if PySide6 / Shiboken is present.

Usage::

    python poc/scripts/verify_no_pyside6.py poc/build
"""

from __future__ import annotations

import sys
from pathlib import Path

FORBIDDEN = ("pyside6", "pyside2", "shiboken6", "shiboken2", "pyqt5", "pyqt6")


def main(root: str) -> int:
    root_path = Path(root)
    if not root_path.exists():
        print(f"path does not exist: {root_path}", file=sys.stderr)
        return 2

    hits: list[Path] = []
    for p in root_path.rglob("*"):
        name = p.name.lower()
        if any(tok in name for tok in FORBIDDEN):
            hits.append(p)

    if hits:
        print("FORBIDDEN Qt-family artifacts found in build tree:")
        for h in hits[:50]:
            print(f"  {h}")
        if len(hits) > 50:
            print(f"  ... and {len(hits) - 50} more")
        return 1

    print(f"No Qt-family artifacts in {root_path}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: verify_no_pyside6.py <path-to-build-tree>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
