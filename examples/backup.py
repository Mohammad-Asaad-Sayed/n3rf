"""Back up the n3rf SQLite database to a timestamped file.

Usage:
    python examples/backup.py [destination_dir]

The backup uses SQLite's online backup API so it is safe even while the
server is running. Set N3RF_DB_PATH to point at a non-default database.
"""
from __future__ import annotations

import datetime
import os
import sqlite3
import sys
from pathlib import Path


def main() -> None:
    src = Path(os.environ.get("N3RF_DB_PATH", "n3rf.sqlite3")).resolve()
    if not src.is_file():
        raise SystemExit(f"Database not found: {src}")
    dest_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = dest_dir / f"n3rf-{stamp}.sqlite3"
    with sqlite3.connect(src) as source, sqlite3.connect(dest) as target:
        source.backup(target)
    print(f"Backed up {src} -> {dest}")


if __name__ == "__main__":
    main()
