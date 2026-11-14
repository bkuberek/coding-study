# pyright: reportMissingImports=false
"""Asks the partner for each member's bonus for a month, and records what it could learn."""

from datetime import date
from typing import Any

from bonus import fetch_bonus
from db import query

RECONCILED = "reconciled"
PENDING = "pending"

UPSERT = (
    "INSERT INTO reconciliations (member, month, status, bonus_points) "
    "VALUES (:member, :month, :status, :bonus) "
    "ON CONFLICT (member, month) DO UPDATE "
    "SET status = EXCLUDED.status, bonus_points = EXCLUDED.bonus_points"
)


def month_bounds(month: str) -> tuple[date, date]:
    """The first day of `month` (`YYYY-MM`) and of the month after it."""
    year, number = int(month[:4]), int(month[5:])
    following = date(year + number // 12, number % 12 + 1, 1)
    return date(year, number, 1), following


def members_who_bought_in(month: str) -> list[str]:
    start, end = month_bounds(month)
    rows = query(
        "SELECT DISTINCT member FROM purchases WHERE purchased_on >= :start AND purchased_on < :end",
        start=start,
        end=end,
    )
    return sorted(member for (member,) in rows)


def reconcile(month: str) -> dict[str, Any]:
    """Looks up every member of `month` the partner has not answered for yet.

    A member that is already reconciled is not asked again. One the partner cannot answer is left
    pending, to be asked again by the next run, and the run still ends normally.
    """
    members = members_who_bought_in(month)
    done = {
        member
        for (member,) in query(
            "SELECT member FROM reconciliations WHERE month = :month AND status = :status",
            month=month,
            status=RECONCILED,
        )
    }
    for member in members:
        if member in done:
            continue
        bonus = fetch_bonus(member, month)
        query(
            UPSERT,
            member=member,
            month=month,
            status=PENDING if bonus is None else RECONCILED,
            bonus=bonus,
        )
        if bonus is not None:
            done.add(member)
    reconciled = sum(1 for member in members if member in done)
    return {
        "month": month,
        "members": len(members),
        "reconciled": reconciled,
        "pending": len(members) - reconciled,
    }
