"""The bank: the class that `cstudy submit` and the tests drive."""

from bank.models import Account


class Bank:
    """Bank accounts that hold whole amounts of money and send money to one another."""

    def __init__(self) -> None:
        self._accounts: dict[str, Account] = {}

    def create_account(self, timestamp: int, account_id: str) -> bool:
        raise NotImplementedError

    def deposit(self, timestamp: int, account_id: str, amount: int) -> int:
        raise NotImplementedError

    def transfer(
        self, timestamp: int, source_id: str, target_id: str, amount: int
    ) -> int:
        raise NotImplementedError
