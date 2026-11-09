def rooms_on(app, day: str) -> dict:
    status, body = app.get(f"/availability?date={day}")
    assert status == 200
    return body["rooms"]


def test_both_vendors_answer_in_one_list(app):
    rooms = rooms_on(app, "2027-03-08")

    assert (len(rooms["slots"]), rooms["unavailable"]) == (5, [])


def test_a_vendor_that_is_down_costs_only_its_own_slots(app, vendors):
    vendors.set_scenario("room-vendor", "outage")

    rooms = rooms_on(app, "2027-03-08")

    assert (len(rooms["slots"]), rooms["unavailable"]) == (3, ["room-vendor"])


def test_both_vendors_down_still_answers_the_desks(app, vendors):
    vendors.set_scenario("room-vendor", "outage")
    vendors.set_scenario("annex-vendor", "maintenance")

    status, body = app.get("/availability?date=2027-03-08")

    assert (status, body) == (
        200,
        {
            "date": "2027-03-08",
            "desks": {"available": 20},
            "rooms": {"slots": [], "unavailable": ["annex-vendor", "room-vendor"]},
        },
    )
