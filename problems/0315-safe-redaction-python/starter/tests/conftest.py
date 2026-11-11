"""Fixtures shared by the tests in this folder."""

import pytest

from redaction.redactor import Redactor


@pytest.fixture
def redactor() -> Redactor:
    """A new redactor, for tests that take a `redactor` argument."""
    return Redactor()
