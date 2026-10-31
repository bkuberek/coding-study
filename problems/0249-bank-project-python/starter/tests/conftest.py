"""Fixtures shared by the tests in this folder."""

import pytest

from bank.bank import Bank


@pytest.fixture
def bank() -> Bank:
    """A new bank with no accounts, for tests that take a `bank` argument."""
    return Bank()
