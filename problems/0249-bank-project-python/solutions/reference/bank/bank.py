"""The bank: the class that `cstudy submit` and the tests drive."""

from typing import Final

from bank.accounts import Accounts
from bank.models import Account
from bank.scheduler import ScheduledTransfer, TransferScheduler

FAILED: Final = -1
NOT_BOOKED: Final = ""


class Bank:
    """Bank accounts that hold whole amounts of money and send money to one another.

    Every public method first runs the scheduled transfers that fell due by its
    timestamp, so it sees the bank as it is at that moment.
    """

    def __init__(self) -> None:
        self._accounts = Accounts()
        self._scheduler = TransferScheduler()

    def create_account(self, timestamp: int, account_id: str) -> bool:
        self._settle(timestamp)
        return self._accounts.create(timestamp, account_id)

    def deposit(self, timestamp: int, account_id: str, amount: int) -> int:
        self._settle(timestamp)
        account = self._accounts.find_open(account_id)
        return FAILED if account is None else account.deposit(timestamp, amount)

    def transfer(
        self, timestamp: int, source_id: str, target_id: str, amount: int
    ) -> int:
        self._settle(timestamp)
        source = self._accounts.find_open(source_id)
        target = self._accounts.find_open(target_id)
        if source is None or target is None or not source.can_send(target, amount):
            return FAILED
        return source.send(target, timestamp, amount)

    def top_spenders(self, timestamp: int, n: int) -> list[str]:
        self._settle(timestamp)
        ranked = sorted(self._accounts.open_accounts(), key=_by_spending)
        return [f"{account.account_id}({account.outgoing})" for account in ranked[:n]]

    def schedule_transfer(
        self, timestamp: int, source_id: str, target_id: str, amount: int, delay: int
    ) -> str:
        self._settle(timestamp)
        source = self._accounts.find_open(source_id)
        target = self._accounts.find_open(target_id)
        if source is None or target is None or source is target:
            return NOT_BOOKED
        transfer = ScheduledTransfer(
            source_id, target_id, amount, due=timestamp + delay
        )
        return self._scheduler.book(transfer)

    def cancel_transfer(
        self, timestamp: int, account_id: str, transfer_id: str
    ) -> bool:
        self._settle(timestamp)
        transfer = self._scheduler.find_pending(transfer_id)
        if transfer is None:
            return False
        sender = self._accounts.holder_of(transfer.source_id)
        if sender.account_id != account_id:
            return False
        self._scheduler.cancel(transfer)
        return True

    def merge_accounts(self, timestamp: int, account_id: str, other_id: str) -> bool:
        self._settle(timestamp)
        return self._accounts.merge(timestamp, account_id, other_id)

    def get_balance(self, timestamp: int, account_id: str, time_at: int) -> int:
        self._settle(timestamp)
        account = self._accounts.find(account_id)
        balance = None if account is None else account.balance_at(time_at)
        return FAILED if balance is None else balance

    def _settle(self, timestamp: int) -> None:
        """Run every scheduled transfer due by `timestamp`, each at its own due time."""
        for transfer in self._scheduler.take_due(timestamp):
            source = self._accounts.holder_of(transfer.source_id)
            target = self._accounts.holder_of(transfer.target_id)
            if source.can_send(target, transfer.amount):
                source.send(target, transfer.due, transfer.amount)


def _by_spending(account: Account) -> tuple[int, str]:
    """Sort key: larger totals sent first, equal totals by id."""
    return -account.outgoing, account.account_id
