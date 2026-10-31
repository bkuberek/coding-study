"""The bank's model types."""

from dataclasses import dataclass


@dataclass(slots=True)
class Account:
    """One bank account."""

    account_id: str
    balance: int = 0
