# pyright: reportMissingImports=false
"""The connection to Postgres, from `DATABASE_URL`."""

import os
from typing import Any
from urllib.parse import urlsplit

import pg8000.native


def connect() -> pg8000.native.Connection:
    url = urlsplit(os.environ["DATABASE_URL"])
    return pg8000.native.Connection(
        url.username or "",
        host=url.hostname,
        port=url.port or 5432,
        database=url.path.lstrip("/"),
        password=url.password,
    )


def query(sql: str, **params: Any) -> list[list[Any]]:
    """Runs one statement on a connection of its own, and returns its rows."""
    database = connect()
    try:
        return database.run(sql, **params)
    finally:
        database.close()
