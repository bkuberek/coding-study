# pyright: reportMissingImports=false
"""`commands.reset`. `prepare` keeps a copy of the migrated database, once, before the app starts;
`apply` puts that copy back and empties the cache, with the app stopped."""

import os
import socket
import sys
from urllib.parse import urlsplit

import pg8000.native

SNAPSHOT = "app_snapshot"
FLUSH = b"*1\r\n$8\r\nFLUSHALL\r\n"


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


def empty_the_cache() -> None:
    url = urlsplit(os.environ["REDIS_URL"])
    with socket.create_connection((url.hostname, url.port or 6379), 5) as cache:
        cache.sendall(FLUSH)
        if not cache.recv(64).startswith(b"+OK"):
            sys.exit("the cache did not empty")


def main() -> None:
    database, name = maintenance()
    if os.environ["CSTUDY_RESET_PHASE"] == "prepare":
        database.run(f"DROP DATABASE IF EXISTS {SNAPSHOT}")
        database.run(f"CREATE DATABASE {SNAPSHOT} TEMPLATE {name}")
    else:
        database.run(f"DROP DATABASE {name} WITH (FORCE)")
        database.run(f"CREATE DATABASE {name} TEMPLATE {SNAPSHOT}")
        empty_the_cache()
    database.close()


if __name__ == "__main__":
    main()
