"""The bank's model types: an account and the history of its balance."""

from bisect import bisect_right
from dataclasses import dataclass, field
from typing import Self


class BalanceHistory:
    """An account's balance after each change, in time order."""

    def __init__(self) -> None:
        self._times: list[int] = []
        self._balances: list[int] = []

    def record(self, timestamp: int, balance: int) -> None:
        self._times.append(timestamp)
        self._balances.append(balance)

    def balance_at(self, moment: int) -> int | None:
        """The balance after the last change at or before `moment`.

        None when `moment` comes before the first change.
        """
        position = bisect_right(self._times, moment)
        return self._balances[position - 1] if position > 0 else None


@dataclass(slots=True, eq=False)
class Account:
    """An account: its balance, the money it sent, its lifetime and its history."""

    account_id: str
    created_at: int
    balance: int = 0
    outgoing: int = 0
    merged_away_at: int | None = None
    history: BalanceHistory = field(
        default_factory=BalanceHistory, init=False, repr=False
    )

    def __post_init__(self) -> None:
        self.history.record(self.created_at, self.balance)

    @property
    def is_open(self) -> bool:
        return self.merged_away_at is None

    def deposit(self, timestamp: int, amount: int) -> int:
        return self._change_balance(timestamp, amount)

    def can_send(self, target: Self, amount: int) -> bool:
        return target is not self and self.balance >= amount

    def send(self, target: Self, timestamp: int, amount: int) -> int:
        """Move `amount` to `target` and return this account's new balance."""
        target.deposit(timestamp, amount)
        self.outgoing += amount
        return self._change_balance(timestamp, -amount)

    def absorb(self, other: Self, timestamp: int) -> None:
        """Add `other`'s balance and total sent to this account and close `other`."""
        self._change_balance(timestamp, other.balance)
        self.outgoing += other.outgoing
        other.merged_away_at = timestamp

    def balance_at(self, moment: int) -> int | None:
        """The balance at `moment`; None when the account did not exist then."""
        if not self.existed_at(moment):
            return None
        return self.history.balance_at(moment)

    def existed_at(self, moment: int) -> bool:
        merged_away = self.merged_away_at is not None and moment >= self.merged_away_at
        return moment >= self.created_at and not merged_away

    def _change_balance(self, timestamp: int, delta: int) -> int:
        self.balance += delta
        self.history.record(timestamp, self.balance)
        return self.balance
