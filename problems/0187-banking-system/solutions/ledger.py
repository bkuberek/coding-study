from bisect import bisect_right
from collections import deque
from dataclasses import dataclass, field

CASHBACK_DELAY = 86_400_000
CASHBACK_PERCENT = 2


@dataclass(slots=True)
class _Account:
    account_id: str
    created_at: int
    balance: int = 0
    outgoing: int = 0
    closed_at: int | None = None
    # (time, balance after the change), in time order: the account's balance history.
    history: list[tuple[int, int]] = field(default_factory=list)

    def change_balance(self, timestamp: int, delta: int) -> int:
        self.balance += delta
        self.history.append((timestamp, self.balance))
        return self.balance

    def balance_at(self, moment: int) -> int:
        if moment < self.created_at or (self.closed_at is not None and moment >= self.closed_at):
            return -1
        position = bisect_right(self.history, moment, key=lambda entry: entry[0])
        return self.history[position - 1][1]


@dataclass(slots=True)
class _Payment:
    payment_id: str
    account_id: str
    cashback: int
    due: int
    received: bool = False


class BankingSystem:
    def __init__(self) -> None:
        self._accounts: dict[str, _Account] = {}
        self._merged_into: dict[str, str] = {}
        self._payments: dict[str, _Payment] = {}
        # The delay is constant and timestamps increase, so cashbacks fall due in payment order.
        self._pending: deque[_Payment] = deque()

    # Level 1
    def create_account(self, timestamp: int, account_id: str) -> bool:
        self._settle(timestamp)
        if account_id in self._accounts:
            return False
        account = _Account(account_id, timestamp)
        account.change_balance(timestamp, 0)
        self._accounts[account_id] = account
        return True

    def deposit(self, timestamp: int, account_id: str, amount: int) -> int:
        self._settle(timestamp)
        account = self._open(account_id)
        return -1 if account is None else account.change_balance(timestamp, amount)

    def transfer(self, timestamp: int, source_id: str, target_id: str, amount: int) -> int:
        self._settle(timestamp)
        source, target = self._open(source_id), self._open(target_id)
        if source is None or target is None or source is target or source.balance < amount:
            return -1
        target.change_balance(timestamp, amount)
        source.outgoing += amount
        return source.change_balance(timestamp, -amount)

    # Level 2
    def top_spenders(self, timestamp: int, n: int) -> list[str]:
        self._settle(timestamp)
        open_accounts = (account for account in self._accounts.values() if account.closed_at is None)
        ranked = sorted(open_accounts, key=lambda account: (-account.outgoing, account.account_id))
        return [f"{account.account_id}({account.outgoing})" for account in ranked[:n]]

    # Level 3
    def pay(self, timestamp: int, account_id: str, amount: int) -> str:
        self._settle(timestamp)
        account = self._open(account_id)
        if account is None or account.balance < amount:
            return ""
        account.change_balance(timestamp, -amount)
        account.outgoing += amount
        payment = _Payment(
            payment_id=f"payment{len(self._payments) + 1}",
            account_id=account_id,
            cashback=amount * CASHBACK_PERCENT // 100,
            due=timestamp + CASHBACK_DELAY,
        )
        self._payments[payment.payment_id] = payment
        self._pending.append(payment)
        return payment.payment_id

    def payment_status(self, timestamp: int, account_id: str, payment_id: str) -> str:
        self._settle(timestamp)
        payment = self._payments.get(payment_id)
        if self._open(account_id) is None or payment is None:
            return ""
        if self._owner(payment.account_id) != account_id:
            return ""
        return "CASHBACK_RECEIVED" if payment.received else "IN_PROGRESS"

    # Level 4
    def merge_accounts(self, timestamp: int, account_id: str, other_id: str) -> bool:
        self._settle(timestamp)
        account, other = self._open(account_id), self._open(other_id)
        if account is None or other is None or account is other:
            return False
        account.change_balance(timestamp, other.balance)
        account.outgoing += other.outgoing
        other.closed_at = timestamp
        self._merged_into[other_id] = account_id
        return True

    def get_balance(self, timestamp: int, account_id: str, time_at: int) -> int:
        self._settle(timestamp)
        account = self._accounts.get(account_id)
        return -1 if account is None else account.balance_at(time_at)

    def _open(self, account_id: str) -> _Account | None:
        account = self._accounts.get(account_id)
        return account if account is not None and account.closed_at is None else None

    def _owner(self, account_id: str) -> str:
        """The open account that now holds `account_id`, following merges."""
        while account_id in self._merged_into:
            account_id = self._merged_into[account_id]
        return account_id

    def _settle(self, timestamp: int) -> None:
        """Credit every cashback due at or before `timestamp`, at its own due time."""
        while self._pending and self._pending[0].due <= timestamp:
            payment = self._pending.popleft()
            owner = self._accounts[self._owner(payment.account_id)]
            owner.change_balance(payment.due, payment.cashback)
            payment.received = True
