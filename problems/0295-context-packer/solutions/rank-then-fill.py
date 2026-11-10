from collections import Counter
from dataclasses import dataclass

OVER_BUDGET = "OVER_BUDGET"
# Two items are near-duplicates when shared / union > 4 / 5, compared in integers.
SIMILARITY_NUMERATOR, SIMILARITY_DENOMINATOR = 4, 5


@dataclass(slots=True)
class _Item:
    item_id: str
    words: frozenset[str]
    tokens: int
    score: int
    pinned: bool = False
    category: str | None = None

    def packing_order(self) -> tuple[bool, int, int, str]:
        """Pinned items first, then higher score, then fewer tokens, then smaller id."""
        return (not self.pinned, -self.score, self.tokens, self.item_id)

    def duplicates(self, other: "_Item") -> bool:
        shared = len(self.words & other.words)
        union = len(self.words) + len(other.words) - shared
        return shared * SIMILARITY_DENOMINATOR > union * SIMILARITY_NUMERATOR


class ContextPacker:
    def __init__(self) -> None:
        self._items: dict[str, _Item] = {}
        self._caps: dict[str, int] = {}

    # Level 1
    def add_item(self, timestamp: int, item_id: str, text: str, tokens: int, score: int) -> bool:
        if item_id in self._items:
            return False
        self._items[item_id] = _Item(item_id, frozenset(text.split()), tokens, score)
        return True

    def remove_item(self, timestamp: int, item_id: str) -> bool:
        return self._items.pop(item_id, None) is not None

    def pack(self, timestamp: int, budget: int) -> list[str]:
        survivors, _ = self._collapse()
        pinned_tokens = sum(item.tokens for item in survivors if item.pinned)
        if pinned_tokens > budget:
            return [OVER_BUDGET]
        remaining = budget
        taken: Counter[str | None] = Counter()
        chosen = []
        for item in survivors:
            if not item.pinned and (item.tokens > remaining or self._is_full(item, taken)):
                continue
            chosen.append(item.item_id)
            remaining -= item.tokens
            taken[item.category] += 1
        return chosen

    # Level 2
    def pin(self, timestamp: int, item_id: str) -> bool:
        item = self._items.get(item_id)
        if item is None or item.pinned:
            return False
        item.pinned = True
        return True

    def unpin(self, timestamp: int, item_id: str) -> bool:
        item = self._items.get(item_id)
        if item is None or not item.pinned:
            return False
        item.pinned = False
        return True

    # Level 3
    def set_category(self, timestamp: int, item_id: str, category: str) -> bool:
        item = self._items.get(item_id)
        if item is None:
            return False
        item.category = category
        return True

    def set_cap(self, timestamp: int, category: str, cap: int) -> None:
        self._caps[category] = cap

    # Level 4
    def duplicate_of(self, timestamp: int, item_id: str) -> str:
        _, knocked_out = self._collapse()
        return knocked_out.get(item_id, "")

    def _is_full(self, item: _Item, taken: Counter[str | None]) -> bool:
        cap = self._caps.get(item.category) if item.category is not None else None
        return cap is not None and taken[item.category] >= cap

    def _collapse(self) -> tuple[list[_Item], dict[str, str]]:
        """The items that survive, in packing order, and which kept item knocked out each other one.

        An unpinned item is knocked out by the first item kept before it that it near-duplicates.
        """
        survivors: list[_Item] = []
        knocked_out: dict[str, str] = {}
        for item in sorted(self._items.values(), key=_Item.packing_order):
            keeper = None
            if not item.pinned:
                keeper = next((kept for kept in survivors if item.duplicates(kept)), None)
            if keeper is None:
                survivors.append(item)
            else:
                knocked_out[item.item_id] = keeper.item_id
        return survivors, knocked_out
