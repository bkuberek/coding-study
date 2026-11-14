import threading
from contextlib import ExitStack


class Bank:
    def __init__(self, balances: list[int]) -> None:
        self._balances = list(balances)
        self._locks = [threading.RLock() for _ in balances]

    def transfer(self, from_account: int, to_account: int, amount: int) -> bool:
        if not (self._exists(from_account) and self._exists(to_account)):
            return False
        with self._locks[from_account]:
            with self._locks[to_account]:
                if self._balances[from_account] < amount:
                    return False
                self._balances[from_account] -= amount
                self._balances[to_account] += amount
                return True

    def balance(self, account: int) -> int:
        if not self._exists(account):
            return -1
        with self._locks[account]:
            return self._balances[account]

    def total(self) -> int:
        with ExitStack() as held:
            for lock in self._locks:
                held.enter_context(lock)
            return sum(self._balances)

    def _exists(self, account: int) -> bool:
        return 0 <= account < len(self._balances)
