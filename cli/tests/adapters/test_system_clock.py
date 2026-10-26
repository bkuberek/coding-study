from datetime import UTC, datetime

from coding_study.adapters.system_clock import SystemClock


def test_now_is_timezone_aware_utc():
    assert SystemClock().now().tzinfo is UTC


def test_local_date_converts_to_the_local_zone():
    instant = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)
    assert SystemClock().local_date(instant) == instant.astimezone().date()


def test_monotonic_never_goes_back():
    clock = SystemClock()
    assert clock.monotonic() <= clock.monotonic()
