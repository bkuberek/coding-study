class Bank:
    def __init__(self, balances: list[int]) -> None:
        self._balances = list(balances)

    def transfer(self, from_account: int, to_account: int, amount: int) -> bool:
        if not (self._exists(from_account) and self._exists(to_account)):
            return False
        source = self._balances[from_account]
        if source < amount:
            return False
        self._balances[from_account] = source - amount
        destination = self._balances[to_account]
        self._balances[to_account] = destination + amount
        return True

    def balance(self, account: int) -> int:
        return self._balances[account] if self._exists(account) else -1

    def total(self) -> int:
        return sum(self._balances)

    def _exists(self, account: int) -> bool:
        return 0 <= account < len(self._balances)
