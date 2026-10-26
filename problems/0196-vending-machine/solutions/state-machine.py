from dataclasses import dataclass
from enum import Enum

IMPOSSIBLE = float("inf")


class State(Enum):
    MAINTENANCE = "MAINTENANCE"
    IDLE = "IDLE"
    HAS_CREDIT = "HAS_CREDIT"


class CoinBox:
    """The coins inside the machine, by denomination; pays out exact change with the fewest coins."""

    def __init__(self, denominations: list[int]) -> None:
        self._counts = {coin: 0 for coin in sorted(denominations, reverse=True)}

    def accepts(self, coin: int) -> bool:
        return coin in self._counts

    def add(self, coin: int, count: int = 1) -> None:
        self._counts[coin] += count

    def pay_out(self, amount: int) -> list[int] | None:
        """Remove and return coins worth `amount`, or None (changing nothing) when impossible."""
        coins = self._plan(amount)
        if coins is not None:
            for coin in coins:
                self._counts[coin] -= 1
        return coins

    def _plan(self, amount: int) -> list[int] | None:
        """Fewest coins; among those, as many of the largest coin as possible, then the next."""
        stock = list(self._counts.items())  # largest denomination first
        # fewest[i][a]: fewest coins making `a` from denominations i and smaller.
        fewest = [[IMPOSSIBLE] * (amount + 1) for _ in range(len(stock) + 1)]
        fewest[len(stock)][0] = 0
        for i in range(len(stock) - 1, -1, -1):
            coin, available = stock[i]
            for a in range(amount + 1):
                for k in range(min(available, a // coin) + 1):
                    fewest[i][a] = min(fewest[i][a], k + fewest[i + 1][a - k * coin])
        if fewest[0][amount] == IMPOSSIBLE:
            return None
        coins, remaining = [], amount
        for i, (coin, available) in enumerate(stock):
            for k in range(min(available, remaining // coin), -1, -1):
                if k + fewest[i + 1][remaining - k * coin] == fewest[i][remaining]:
                    coins += [coin] * k
                    remaining -= k * coin
                    break
        return coins


@dataclass(slots=True)
class _Slot:
    price: int
    count: int


class VendingMachine:
    def __init__(self, denominations: list[int]) -> None:
        self._state = State.MAINTENANCE
        self._coins = CoinBox(denominations)
        self._slots: dict[str, _Slot] = {}
        self._credit = 0
        self._tray: list[int] = []

    def service(self, enabled: bool) -> bool:
        if enabled and self._state is State.IDLE:
            self._state = State.MAINTENANCE
            return True
        if not enabled and self._state is State.MAINTENANCE:
            self._state = State.IDLE
            return True
        return False

    def stock(self, slot: str, price: int, count: int) -> bool:
        if self._state is not State.MAINTENANCE:
            return False
        item = self._slots.setdefault(slot, _Slot(price, 0))
        item.price, item.count = price, item.count + count
        return True

    def load_coins(self, coin: int, count: int) -> bool:
        if self._state is not State.MAINTENANCE or not self._coins.accepts(coin):
            return False
        self._coins.add(coin, count)
        return True

    def insert(self, coin: int) -> int:
        if self._state is State.MAINTENANCE or not self._coins.accepts(coin):
            self._tray.append(coin)
            return -1
        self._coins.add(coin)
        self._credit += coin
        self._state = State.HAS_CREDIT
        return self._credit

    def select(self, slot: str) -> str:
        if self._state is State.MAINTENANCE:
            return "OUT_OF_SERVICE"
        item = self._slots.get(slot)
        if item is None:
            return "UNKNOWN_SLOT"
        if item.count == 0:
            return "SOLD_OUT"
        if self._credit < item.price:
            return "INSUFFICIENT_CREDIT"
        change = self._coins.pay_out(self._credit - item.price)
        if change is None:
            return "NO_CHANGE"
        item.count -= 1
        self._finish(change)
        return "DISPENSED"

    def refund(self) -> int:
        if self._state is not State.HAS_CREDIT:
            return 0
        amount = self._credit
        self._finish(self._coins.pay_out(amount) or [])
        return amount

    def collect(self) -> list[int]:
        coins, self._tray = sorted(self._tray, reverse=True), []
        return coins

    def state(self) -> str:
        return self._state.value

    def stock_of(self, slot: str) -> int:
        item = self._slots.get(slot)
        return -1 if item is None else item.count

    def _finish(self, change: list[int]) -> None:
        """Return change to the tray and end the transaction."""
        self._tray += change
        self._credit = 0
        self._state = State.IDLE
