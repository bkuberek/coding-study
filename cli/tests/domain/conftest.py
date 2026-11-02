import pytest

from coding_study.domain import virtual_clock


@pytest.fixture
def graded_clock_runners(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every language that can declare the virtual clock has a runner that grades it.

    Today none has (`GRADED_CLOCK_LANGUAGES` is empty until the first runner lands), so the checks
    of a declaration beyond its language need this to see a clock that a runner grades.
    """
    monkeypatch.setattr(
        virtual_clock, "GRADED_CLOCK_LANGUAGES", frozenset(virtual_clock.CLOCK_LANGUAGES)
    )
