"""Every account by id, merged-away ones included, and who holds an id now."""

from collections.abc import Iterator

from bank.models import Account


class Accounts:
    """The bank's accounts. A merged-away account keeps its id and its history."""

    def __init__(self) -> None:
        self._by_id: dict[str, Account] = {}
        self._merged_into: dict[str, str] = {}

    def create(self, timestamp: int, account_id: str) -> bool:
        """Open an account; False when the id is taken, even by a merged-away one."""
        if account_id in self._by_id:
            return False
        self._by_id[account_id] = Account(account_id, created_at=timestamp)
        return True

    def find(self, account_id: str) -> Account | None:
        """The account with this id, open or merged away."""
        return self._by_id.get(account_id)

    def find_open(self, account_id: str) -> Account | None:
        account = self._by_id.get(account_id)
        return account if account is not None and account.is_open else None

    def open_accounts(self) -> Iterator[Account]:
        return (account for account in self._by_id.values() if account.is_open)

    def merge(self, timestamp: int, account_id: str, other_id: str) -> bool:
        """Fold `other_id` into `account_id`.

        Returns False, changing nothing, when the ids are equal or either account
        is not open.
        """
        kept, absorbed = self.find_open(account_id), self.find_open(other_id)
        if kept is None or absorbed is None or kept is absorbed:
            return False
        kept.absorb(absorbed, timestamp)
        self._merged_into[other_id] = account_id
        return True

    def holder_of(self, account_id: str) -> Account:
        """The open account that holds `account_id` now, following its merges."""
        while account_id in self._merged_into:
            account_id = self._merged_into[account_id]
        return self._by_id[account_id]
