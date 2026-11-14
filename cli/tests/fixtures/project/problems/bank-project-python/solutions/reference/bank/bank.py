class Bank:
    """Accounts that hold a balance, keyed by account id."""

    def __init__(self) -> None:
        self._balances: dict[str, int] = {}

    def create_account(self, timestamp: int, account_id: str) -> bool:
        if account_id in self._balances:
            return False
        self._balances[account_id] = 0
        return True

    def deposit(self, timestamp: int, account_id: str, amount: int) -> int:
        if account_id not in self._balances:
            return -1
        self._balances[account_id] += amount
        return self._balances[account_id]

    def transfer(self, timestamp: int, source_id: str, target_id: str, amount: int) -> int:
        balances = self._balances
        known = source_id in balances and target_id in balances
        if not known or source_id == target_id or balances[source_id] < amount:
            return -1
        balances[source_id] -= amount
        balances[target_id] += amount
        return balances[source_id]
