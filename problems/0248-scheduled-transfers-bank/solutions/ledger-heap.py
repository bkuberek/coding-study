import heapq
from bisect import bisect_right
from dataclasses import dataclass, field


@dataclass(slots=True)
class _Account:
    account_id: str
    created_at: int
    balance: int = 0
    outgoing: int = 0
    closed_at: int | None = None
    # (time, balance after the change), in time order: the account's balance history.
    history: list[tuple[int, int]] = field(default_factory=list)

    @property
    def is_open(self) -> bool:
        return self.closed_at is None

    def change_balance(self, timestamp: int, delta: int) -> int:
        self.balance += delta
        self.history.append((timestamp, self.balance))
        return self.balance

    def balance_at(self, moment: int) -> int:
        if moment < self.created_at or (self.closed_at is not None and moment >= self.closed_at):
            return -1
        position = bisect_right(self.history, moment, key=lambda entry: entry[0])
        return self.history[position - 1][1]

    def can_send(self, target: "_Account", amount: int) -> bool:
        return self is not target and self.balance >= amount

    def send(self, target: "_Account", timestamp: int, amount: int) -> int:
        target.change_balance(timestamp, amount)
        self.outgoing += amount
        return self.change_balance(timestamp, -amount)


@dataclass(slots=True)
class _ScheduledTransfer:
    transfer_id: str
    source_id: str
    target_id: str
    amount: int
    due: int
    pending: bool = True


class Bank:
    def __init__(self) -> None:
        self._accounts: dict[str, _Account] = {}
        self._merged_into: dict[str, str] = {}
        self._transfers: dict[str, _ScheduledTransfer] = {}
        # (due, number, transfer): earliest due first, ties in scheduling order. A cancelled
        # transfer stays in the heap and is dropped when it reaches the top.
        self._due: list[tuple[int, int, _ScheduledTransfer]] = []

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
        if source is None or target is None or not source.can_send(target, amount):
            return -1
        return source.send(target, timestamp, amount)

    # Level 2
    def top_spenders(self, timestamp: int, n: int) -> list[str]:
        self._settle(timestamp)
        open_accounts = (account for account in self._accounts.values() if account.is_open)
        ranked = sorted(open_accounts, key=lambda account: (-account.outgoing, account.account_id))
        return [f"{account.account_id}({account.outgoing})" for account in ranked[:n]]

    # Level 3
    def schedule_transfer(
        self, timestamp: int, source_id: str, target_id: str, amount: int, delay: int
    ) -> str:
        self._settle(timestamp)
        source, target = self._open(source_id), self._open(target_id)
        if source is None or target is None or source is target:
            return ""
        number = len(self._transfers) + 1
        scheduled = _ScheduledTransfer(
            transfer_id=f"transfer{number}",
            source_id=source_id,
            target_id=target_id,
            amount=amount,
            due=timestamp + delay,
        )
        self._transfers[scheduled.transfer_id] = scheduled
        heapq.heappush(self._due, (scheduled.due, number, scheduled))
        return scheduled.transfer_id

    def cancel_transfer(self, timestamp: int, account_id: str, transfer_id: str) -> bool:
        self._settle(timestamp)
        scheduled = self._transfers.get(transfer_id)
        if self._open(account_id) is None or scheduled is None or not scheduled.pending:
            return False
        if self._owner(scheduled.source_id) != account_id:
            return False
        scheduled.pending = False
        return True

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
        return account if account is not None and account.is_open else None

    def _owner(self, account_id: str) -> str:
        """The open account that now holds `account_id`, following merges."""
        while account_id in self._merged_into:
            account_id = self._merged_into[account_id]
        return account_id

    def _settle(self, timestamp: int) -> None:
        """Run every scheduled transfer due at or before `timestamp`, each at its own due time."""
        while self._due and self._due[0][0] <= timestamp:
            _, _, scheduled = heapq.heappop(self._due)
            if not scheduled.pending:
                continue
            scheduled.pending = False
            source = self._accounts[self._owner(scheduled.source_id)]
            target = self._accounts[self._owner(scheduled.target_id)]
            if source.can_send(target, scheduled.amount):
                source.send(target, scheduled.due, scheduled.amount)
