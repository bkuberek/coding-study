# pyright: reportMissingImports=false
"""`commands.reset`: puts the database back as `bootstrap` left it.

`prepare` runs once, after `bootstrap`, and keeps a copy of the migrated database. `apply` runs
between cases, with the app stopped, and replaces the database by that copy. It works for any
tables your migrations create, so you never need to edit it.
"""

import os
from urllib.parse import urlsplit

import pg8000.native

SNAPSHOT = "app_snapshot"


def maintenance() -> tuple[pg8000.native.Connection, str]:
    """A connection to the server's own database, and the name of the app's."""
    url = urlsplit(os.environ["DATABASE_URL"])
    connection = pg8000.native.Connection(
        url.username or "",
        host=url.hostname,
        port=url.port or 5432,
        database="postgres",
        password=url.password,
    )
    return connection, url.path.lstrip("/")


def main() -> None:
    database, name = maintenance()
    if os.environ["CSTUDY_RESET_PHASE"] == "prepare":
        database.run(f"DROP DATABASE IF EXISTS {SNAPSHOT}")
        database.run(f"CREATE DATABASE {SNAPSHOT} TEMPLATE {name}")
    else:
        database.run(f"DROP DATABASE {name} WITH (FORCE)")
        database.run(f"CREATE DATABASE {name} TEMPLATE {SNAPSHOT}")
    database.close()


if __name__ == "__main__":
    main()
