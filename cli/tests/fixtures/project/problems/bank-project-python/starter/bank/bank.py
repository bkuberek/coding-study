class Bank:
    """Accounts that hold a balance."""

    def create_account(self, timestamp: int, account_id: str) -> bool:
        raise NotImplementedError

    def deposit(self, timestamp: int, account_id: str, amount: int) -> int:
        raise NotImplementedError
