from uuid import uuid4

FEED = """id,member,date,category,amount
{p}1,{m},2027-03-01,grocery,42.50
{p}2,{m},2027-03-02,fuel,30
"""


def test_a_feed_of_good_rows_loads_every_row(app):
    """Each run uses a member of its own, since the database keeps what earlier runs loaded."""
    member = f"m{uuid4().hex[:8]}"

    status, body = app.put("/feeds/mine.csv", FEED.format(p=member, m=member))

    assert (status, body) == (
        200,
        {"feed": "mine.csv", "rows": 2, "loaded": 2, "existing": 0, "rejected": 0},
    )


def test_the_loaded_purchases_are_listed_for_their_member(app):
    member = f"m{uuid4().hex[:8]}"
    app.put("/feeds/mine.csv", FEED.format(p=member, m=member))

    status, body = app.get(f"/purchases?member={member}")

    assert status == 200
    assert [row["amount_cents"] for row in body] == [4250, 3000]
