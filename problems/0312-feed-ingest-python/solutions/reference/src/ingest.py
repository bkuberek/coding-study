# pyright: reportMissingImports=false
"""Loads a feed into Postgres, once however often it is sent."""

from dataclasses import dataclass
from typing import Any

from db import connect, query
from feeds import Feed, read_feed


@dataclass(frozen=True)
class LoadResult:
    rows: int
    loaded: int
    existing: int
    rejected: int


def known_categories() -> set[str]:
    return {code for (code,) in query("SELECT code FROM categories")}


def load_feed(name: str, text: str) -> LoadResult | None:
    """Loads the feed called `name`, or returns None when its header is wrong.

    One transaction holds the whole load. It first locks the feed's own row, so two loads of the
    same name take turns instead of both rewriting its reject report. Purchases go in sorted by
    id, so two loads of different feeds that share ids take the same row locks in the same order
    and cannot deadlock.
    """
    feed = read_feed(text, known_categories())
    if feed is None:
        return None
    database = connect()
    try:
        database.run("START TRANSACTION")
        loaded = store(database, name, feed)
        database.run("COMMIT")
    except BaseException:
        database.run("ROLLBACK")
        raise
    finally:
        database.close()
    return LoadResult(feed.rows, loaded, len(feed.purchases) - loaded, len(feed.rejects))


def store(database: Any, name: str, feed: Feed) -> int:
    """Writes `feed` inside the open transaction and returns how many purchases were new."""
    database.run("INSERT INTO feeds (name) VALUES (:name) ON CONFLICT DO NOTHING", name=name)
    database.run("SELECT name FROM feeds WHERE name = :name FOR UPDATE", name=name)
    database.run("DELETE FROM feed_rejects WHERE feed = :name", name=name)
    for reject in feed.rejects:
        database.run(
            "INSERT INTO feed_rejects (feed, line, reason) VALUES (:feed, :line, :reason)",
            feed=name,
            line=reject.line,
            reason=reject.reason,
        )
    loaded = 0
    for purchase in sorted(feed.purchases, key=lambda purchase: purchase.id):
        inserted = database.run(
            "INSERT INTO purchases (id, member, purchased_on, category, amount_cents) "
            "VALUES (:id, :member, :day, :category, :cents) "
            "ON CONFLICT (id) DO NOTHING RETURNING id",
            id=purchase.id,
            member=purchase.member,
            day=purchase.day,
            category=purchase.category,
            cents=purchase.amount_cents,
        )
        loaded += len(inserted)
    return loaded


def rejects_of(name: str) -> list[dict[str, Any]] | None:
    """The reject report of the feed called `name`, or None when no such feed was loaded."""
    if not query("SELECT 1 FROM feeds WHERE name = :name", name=name):
        return None
    rows = query("SELECT line, reason FROM feed_rejects WHERE feed = :name ORDER BY line", name=name)
    return [{"line": line, "reason": reason} for line, reason in rows]
