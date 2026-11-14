def test_the_service_answers_its_health_path(app):
    status, _ = app.get("/health")

    assert status == 200


def test_a_day_on_sale_answers_its_count(app):
    assert app.get("/desks?date=2027-03-01") == (
        200,
        {"date": "2027-03-01", "available": 12},
    )


def test_no_date_is_a_bad_request(app):
    assert app.get("/desks") == (400, {"error": "date is required"})
