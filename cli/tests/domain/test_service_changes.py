"""What puts a backing service back as its stack started it, after a case changed it."""

import pytest

from coding_study.domain.sandbox import ServiceAction, ServiceChange


@pytest.mark.parametrize(
    ("action", "undoing"),
    [(ServiceAction.PAUSE, ServiceAction.UNPAUSE), (ServiceAction.STOP, ServiceAction.START)],
)
def test_a_change_that_takes_a_service_away_is_undone(action, undoing):
    assert ServiceChange("store", action).undoing() == ServiceChange("store", undoing)


@pytest.mark.parametrize("action", [ServiceAction.UNPAUSE, ServiceAction.START])
def test_a_change_that_brings_a_service_back_needs_no_undoing(action):
    assert ServiceChange("store", action).undoing() is None
