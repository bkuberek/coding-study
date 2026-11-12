import re
from dataclasses import dataclass

OVERHEAD = 4
WORD_PIECE = 4
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+|[^ \tA-Za-z0-9\n]")
NO_LIMIT = -1
SYSTEM, CALL, RESULT = "system", "call", "result"


def _count_tokens(text: str) -> int:
    """A run of letters and digits costs one token for each 4 characters, rounded up; any other
    character that is not white space costs one."""
    return sum(
        -(-len(piece) // WORD_PIECE) if piece[0].isalnum() else 1
        for piece in TOKEN_PATTERN.findall(text)
    )


def _cost(content: str) -> int:
    return _count_tokens(content) + OVERHEAD


@dataclass(slots=True)
class _Turn:
    role: str
    content: str
    call_id: str


@dataclass(slots=True)
class _Item:
    kind: str
    ref: str
    content: str

    @property
    def cost(self) -> int:
        return _cost(self.content)


def _shared_prefix_cost(old: list[_Item], new: list[_Item]) -> int:
    """The tokens of the leading items that two prompts have in common, kind and text alike."""
    shared = 0
    for before, after in zip(old, new, strict=False):
        if (before.kind, before.content) != (after.kind, after.content):
            break
        shared += after.cost
    return shared


class ContextWindow:
    def __init__(self) -> None:
        self._turns: list[_Turn] = []
        self._units: list[list[int]] = []
        self._live_units: list[int] = []
        self._answered: set[str] = set()
        self._calls: set[str] = set()
        self._queue: list[str] = []
        self._next_summary = 0
        self._threshold = NO_LIMIT
        self._keep_recent = 1
        self._low_water = NO_LIMIT
        self._summaries: list[tuple[int, str]] = []
        self._compactions = 0
        self._previous: list[_Item] = []
        self._reuse: list[int] = []
        self._facts: dict[str, str] = {}
        self._pin_budget = NO_LIMIT
        self._block: list[str] = []
        self._compacted: list[int] = []

    # Level 1
    def count_tokens(self, text: str) -> int:
        return _count_tokens(text)

    def add_turn(self, role: str, content: str) -> int:
        return self._append(role, content, "")

    def window(self, budget: int, max_turns: int) -> list[int]:
        system = [i for i, turn in enumerate(self._turns) if turn.role == SYSTEM]
        remaining = budget - sum(_cost(self._turns[i].content) for i in system)
        chosen: list[int] = []
        for unit in reversed(self._units):
            cost = sum(_cost(self._turns[i].content) for i in unit)
            if len(chosen) + len(unit) > max_turns or cost > remaining:
                break
            chosen = unit + chosen
            remaining -= cost
        return system + chosen

    # Level 2
    def add_call(self, call_id: str, content: str) -> int:
        if call_id in self._calls:
            return -1
        self._calls.add(call_id)
        return self._append(CALL, content, call_id)

    def add_result(self, call_id: str, content: str) -> int:
        if call_id not in self._calls or call_id in self._answered:
            return -1
        self._answered.add(call_id)
        return self._append(RESULT, content, call_id)

    def set_summaries(self, texts: list[str]) -> None:
        self._queue = list(texts)
        self._next_summary = 0

    def set_compaction(self, threshold: int, keep_recent: int) -> None:
        self._threshold = threshold
        self._keep_recent = keep_recent

    def context(self) -> list[list[str]]:
        return [[item.kind, item.ref, str(item.cost)] for item in self._items()]

    def compactions(self) -> int:
        return self._compactions

    # Level 3
    def set_stable_prefix(self, low_water: int) -> None:
        self._low_water = low_water

    def prefix_reuse(self) -> list[int]:
        return list(self._reuse)

    # Level 4
    def pin_fact(self, fact_id: str, text: str) -> bool:
        if fact_id in self._facts:
            return False
        self._facts[fact_id] = text
        self._block = self._block_for(self._items_without_block())
        return True

    def set_pin_budget(self, tokens: int) -> None:
        self._pin_budget = tokens

    def recall(self, fact_id: str) -> bool:
        text = self._facts.get(fact_id)
        return text is not None and any(text in item.content for item in self._items())

    def dropped(self) -> list[list[str]]:
        rows = [["turn", str(index)] for index in sorted(self._compacted)]
        rows += [["fact", fact_id] for fact_id in self._facts if not self.recall(fact_id)]
        return rows

    def _append(self, role: str, content: str, call_id: str) -> int:
        index = len(self._turns)
        self._turns.append(_Turn(role, content, call_id))
        if role != SYSTEM:
            joins = (
                role in (CALL, RESULT)
                and index > 0
                and self._turns[index - 1].role in (CALL, RESULT)
            )
            if joins:
                self._units[-1].append(index)
            else:
                self._units.append([index])
                self._live_units.append(len(self._units) - 1)
        self._compact_if_needed()
        prompt = self._items()
        self._reuse.append(_shared_prefix_cost(self._previous, prompt))
        self._previous = prompt
        return index

    def _turn_item(self, index: int) -> _Item:
        turn = self._turns[index]
        return _Item(turn.role, str(index), turn.content)

    def _live_turns(self, units: list[int]) -> list[int]:
        return [index for unit in units for index in self._units[unit]]

    def _items_without_block(self, units=None, summaries=None) -> list[_Item]:
        units = self._live_units if units is None else units
        summaries = self._summaries if summaries is None else summaries
        system = [i for i, turn in enumerate(self._turns) if turn.role == SYSTEM]
        items = [self._turn_item(i) for i in system]
        items += [_Item("summary", str(position), text) for position, text in summaries]
        items += [self._turn_item(i) for i in self._live_turns(units)]
        return items

    def _block_for(self, others: list[_Item]) -> list[str]:
        chosen: list[str] = []
        used = OVERHEAD
        for fact_id, text in self._facts.items():
            if any(text in item.content for item in others):
                continue
            cost = _count_tokens(text)
            if self._pin_budget != NO_LIMIT and used + cost > self._pin_budget:
                continue
            chosen.append(fact_id)
            used += cost
        return chosen

    def _items(self, units=None, summaries=None, block=None) -> list[_Item]:
        others = self._items_without_block(units, summaries)
        block = self._block if block is None else block
        if not block:
            return others
        system_and_summaries = [item for item in others if item.kind in (SYSTEM, "summary")]
        rest = others[len(system_and_summaries) :]
        pinned = _Item("pinned", ",".join(block), "\n".join(self._facts[f] for f in block))
        return [*system_and_summaries, pinned, *rest]

    def _total(self, items: list[_Item]) -> int:
        return sum(item.cost for item in items)

    def _compact_if_needed(self) -> None:
        if self._threshold == NO_LIMIT or self._total(self._items()) <= self._threshold:
            return
        if self._next_summary >= len(self._queue):
            return
        candidates = self._live_units[: max(len(self._live_units) - self._keep_recent, 0)]
        if not candidates:
            return
        position, text = self._next_summary, self._queue[self._next_summary]
        append = self._low_water != NO_LIMIT
        target = self._low_water if append else self._threshold
        for count in range(1, len(candidates) + 1):
            units = self._live_units[count:]
            summaries = [*self._summaries, (position, text)] if append else [(position, text)]
            block = self._block_for(self._items_without_block(units, summaries))
            if self._total(self._items(units, summaries, block)) <= target or count == len(
                candidates
            ):
                break
        self._compacted += self._live_turns(self._live_units[:count])
        self._live_units = units
        self._summaries = summaries
        self._block = block
        self._next_summary += 1
        self._compactions += 1
