# pyright: reportMissingImports=false
"""Problem-owned `grade_setup`: applies only the baseline, recorded as scripts/migrate.py records a
migration, then loads the hidden rows into it. `bootstrap` applies the rest afterwards, so your
migrations must carry these rows forward. Hidden ids start at 900, which the statement reserves."""

import hashlib
import os
from pathlib import Path
from urllib.parse import urlsplit

import pg8000.native

BASELINE = Path(__file__).resolve().parent / "baseline" / "0001_baseline.sql"
TRACKING = (
    "CREATE TABLE IF NOT EXISTS schema_migrations "
    "(version text PRIMARY KEY, checksum text NOT NULL)"
)
RECORD = "INSERT INTO schema_migrations (version, checksum) VALUES (:version, :checksum)"
HIDDEN_ROWS = "INSERT INTO members (id, name) VALUES (900, 'Hidden')"


def main() -> None:
    url = urlsplit(os.environ["DATABASE_URL"])
    database = pg8000.native.Connection(
        url.username or "",
        host=url.hostname,
        port=url.port or 5432,
        database=url.path.lstrip("/"),
        password=url.password,
    )
    text = BASELINE.read_text(encoding="utf-8")
    database.run(TRACKING)
    database.run("START TRANSACTION")
    database.execute_simple(text)
    database.run(RECORD, version=BASELINE.stem, checksum=hashlib.sha256(text.encode()).hexdigest())
    database.execute_simple(HIDDEN_ROWS)
    database.run("COMMIT")
    database.close()


if __name__ == "__main__":
    main()
