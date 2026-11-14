# pyright: reportMissingImports=false
"""Applies each file in migrations/ that has not run yet, in name order, each in a transaction of its
own, and records it with its checksum. A migration that changed after it ran stops the run."""

import hashlib
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

import pg8000.native

MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"
TRACKING = (
    "CREATE TABLE IF NOT EXISTS schema_migrations "
    "(version text PRIMARY KEY, checksum text NOT NULL)"
)
RECORD = (
    "INSERT INTO schema_migrations (version, checksum) VALUES (:version, :checksum)"
)


def connect() -> pg8000.native.Connection:
    url = urlsplit(os.environ["DATABASE_URL"])
    return pg8000.native.Connection(
        url.username or "",
        host=url.hostname,
        port=url.port or 5432,
        database=url.path.lstrip("/"),
        password=url.password,
    )


def main() -> None:
    database = connect()
    database.run(TRACKING)
    applied = dict(database.run("SELECT version, checksum FROM schema_migrations"))
    for path in sorted(MIGRATIONS.glob("*.sql")):
        text = path.read_text(encoding="utf-8")
        checksum = hashlib.sha256(text.encode()).hexdigest()
        if path.stem in applied:
            if applied[path.stem] != checksum:
                sys.exit(f"{path.name} changed after it was applied")
            continue
        database.run("START TRANSACTION")
        database.execute_simple(text)
        database.run(RECORD, version=path.stem, checksum=checksum)
        database.run("COMMIT")
        print(f"applied {path.name}", flush=True)
    database.close()


if __name__ == "__main__":
    main()
