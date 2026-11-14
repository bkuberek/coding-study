# pyright: reportMissingImports=false
"""What a member has earned, worked out from their purchases each time it is asked.

Nothing is stored: points depend on the order of a month's purchases, and a later feed can bring
an earlier purchase, so a stored total would be wrong the moment one arrives out of order.
"""

from typing import Any

from db import query
from points import Spend, points_per_month


def spends_of(member: str) -> list[Spend]:
    rows = query(
        "SELECT id, purchased_on, category, amount_cents FROM purchases WHERE member = :member",
        member=member,
    )
    return [Spend(id_, day, category, cents) for id_, day, category, cents in rows]


def total_points(member: str) -> dict[str, Any] | None:
    spends = spends_of(member)
    if not spends:
        return None
    return {"member": member, "points": sum(points_per_month(spends).values())}


def statement(member: str, month: str) -> dict[str, Any] | None:
    """The member's points for `month` and what the partner granted, or None for no such member."""
    spends = spends_of(member)
    if not spends:
        return None
    rows = query(
        "SELECT status, bonus_points FROM reconciliations WHERE member = :member AND month = :month",
        member=member,
        month=month,
    )
    status, bonus = rows[0] if rows else ("open", None)
    return {
        "member": member,
        "month": month,
        "points": points_per_month(spends).get(month, 0),
        "bonus": bonus,
        "status": status,
    }
