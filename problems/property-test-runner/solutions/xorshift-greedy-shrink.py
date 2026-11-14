from collections import deque

MASK = 0xFFFFFFFF


class GiveUp(Exception):
    """Raised when a call has discarded more values than its limit allows."""


class Random:
    """xorshift32 with the shifts 13, 17 and 5, kept to 32 bits after every left shift."""

    def __init__(self, seed: int, limit: int) -> None:
        self.state = seed & MASK
        self.discards = 0
        self.limit = limit

    def next(self) -> int:
        x = self.state
        x ^= (x << 13) & MASK
        x ^= x >> 17
        x ^= (x << 5) & MASK
        self.state = x
        return x

    def between(self, low: int, high: int) -> int:
        return low + self.next() % (high - low + 1)

    def discard(self) -> None:
        self.discards += 1
        if self.discards > self.limit:
            raise GiveUp


def parse(tokens: list[str], at: int = 0) -> tuple[tuple, int]:
    """Reads one generator from the prefix tokens; returns it and the position after it."""
    head = tokens[at]
    if head == "int":
        return ("int", int(tokens[at + 1]), int(tokens[at + 2])), at + 3
    if head == "list":
        element, end = parse(tokens, at + 3)
        return ("list", int(tokens[at + 1]), int(tokens[at + 2]), element), end
    if head == "pair":
        first, middle = parse(tokens, at + 1)
        second, end = parse(tokens, middle)
        return ("pair", first, second), end
    inner, end = parse(tokens, at + 2)
    return ("filter", tokens[at + 1], inner), end


def generator(text: str) -> tuple:
    return parse(text.split(" "))[0]


def draw(gen: tuple, rng: Random):
    kind = gen[0]
    if kind == "int":
        return rng.between(gen[1], gen[2])
    if kind == "list":
        length = rng.between(gen[1], gen[2])
        return [draw(gen[3], rng) for _ in range(length)]
    if kind == "pair":
        first = draw(gen[1], rng)
        return (first, draw(gen[2], rng))
    while True:
        value = draw(gen[2], rng)
        if passes_filter(gen[1], value):
            return value
        rng.discard()


def text(value) -> str:
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list):
        return "[" + ",".join(text(item) for item in value) + "]"
    return "(" + text(value[0]) + "," + text(value[1]) + ")"


def passes_filter(name: str, value) -> bool:
    if name == "even":
        return value % 2 == 0
    if name == "odd":
        return value % 2 != 0
    if name == "nonzero":
        return value != 0
    if name == "positive":
        return value > 0
    if name == "nonempty":
        return len(value) > 0
    if name == "distinct":
        return len({text(item) for item in value}) == len(value)
    return text(value[0]) != text(value[1])


def total(value) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, list):
        return sum(total(item) for item in value)
    return total(value[0]) + total(value[1])


def ordered(values: list) -> bool:
    return all(values[i] <= values[i + 1] for i in range(len(values) - 1))


def holds(prop: str, value) -> bool:
    name, *rest = prop.split(" ")
    k = int(rest[0]) if rest else 0
    if name == "lt":
        return value < k
    if name == "not-multiple":
        return value % k != 0
    if name == "sum-lt":
        return total(value) < k
    if name == "len-lt":
        return len(value) < k
    if name == "ordered":
        return ordered(value)
    if name == "sort-ordered":
        return ordered(sorted(value))
    if name == "one-pass-ordered":
        items = list(value)
        for i in range(len(items) - 1):
            if items[i] > items[i + 1]:
                items[i], items[i + 1] = items[i + 1], items[i]
        return ordered(items)
    if name == "max-from-zero":
        best = 0
        for item in value:
            best = max(best, item)
        return not value or best == max(value)
    if name == "keys-distinct":
        return len({text(key) for key, _ in value}) == len(value)
    first: dict[str, str] = {}
    last: dict[str, str] = {}
    for key, item in value:
        first.setdefault(text(key), text(item))
        last[text(key)] = text(item)
    return first == last


def halve(number: int) -> int:
    """Half of a number, rounded toward zero (Python's // rounds down)."""
    return number // 2 if number >= 0 else -((-number) // 2)


def int_candidates(low: int, high: int, value: int) -> list[int]:
    target = low if low > 0 else high if high < 0 else 0
    if value == target:
        return []
    found = [target]
    step = halve(value - target)
    while step != 0:
        found.append(value - step)
        step = halve(step)
    return found


def without_repeats(value, found: list) -> list:
    seen = {text(value)}
    kept = []
    for candidate in found:
        key = text(candidate)
        if key not in seen:
            seen.add(key)
            kept.append(candidate)
    return kept


def removals(items: list, shortest: int) -> list[list]:
    n = len(items)
    found = []
    size = n
    while size >= 1:
        if n - size >= shortest:
            for start in range(0, n - size + 1, size):
                found.append(items[:start] + items[start + size :])
        size //= 2
    return found


def candidates_of(gen: tuple, value) -> list:
    kind = gen[0]
    if kind == "int":
        found = int_candidates(gen[1], gen[2], value)
    elif kind == "list":
        found = removals(value, gen[1])
        for i, item in enumerate(value):
            for smaller in candidates_of(gen[3], item):
                found.append(value[:i] + [smaller] + value[i + 1 :])
    elif kind == "pair":
        found = [(smaller, value[1]) for smaller in candidates_of(gen[1], value[0])]
        found += [(value[0], smaller) for smaller in candidates_of(gen[2], value[1])]
    else:
        found = [c for c in candidates_of(gen[2], value) if passes_filter(gen[1], c)]
    return without_repeats(value, found)


class Queue:
    """A bounded first-in first-out queue with one planted bug, or none."""

    def __init__(self, capacity: int, bug: str) -> None:
        self.capacity = capacity
        self.bug = bug
        self.items: deque[int] = deque()
        self.puts = 0

    def allows(self, command: str) -> bool:
        return command != "get" or len(self.items) > 0

    def apply(self, command: str) -> str:
        if command == "size":
            count = len(self.items)
            return str(count % self.capacity if self.bug == "size-wraps" else count)
        if command == "get":
            if not self.items:
                return "empty"
            if self.bug == "wrap-lifo" and self.puts > self.capacity:
                return str(self.items.pop())
            return str(self.items.popleft())
        value = int(command.split(" ")[1])
        if len(self.items) == self.capacity:
            if self.bug != "full-overwrites":
                return "full"
            self.items.popleft()
        elif self.bug == "repeat-dropped" and self.items and self.items[-1] == value:
            self.puts += 1
            return "ok"
        self.items.append(value)
        self.puts += 1
        return "ok"


def valid(capacity: int, commands: list[str]) -> bool:
    model = Queue(capacity, "none")
    for command in commands:
        if not model.allows(command):
            return False
        model.apply(command)
    return True


def fails(capacity: int, bug: str, commands: list[str]) -> bool:
    model, system = Queue(capacity, "none"), Queue(capacity, bug)
    return any(model.apply(c) != system.apply(c) for c in commands)


def sequence(capacity: int, rng: Random, longest: int) -> list[str]:
    model = Queue(capacity, "none")
    commands = []
    for _ in range(rng.between(1, longest)):
        allowed = ["put", "get", "size"] if model.items else ["put", "size"]
        command = allowed[rng.next() % len(allowed)]
        if command == "put":
            command = f"put {rng.between(0, 9)}"
        model.apply(command)
        commands.append(command)
    return commands


def sequence_candidates(capacity: int, commands: list[str]) -> list[list[str]]:
    found = removals(commands, 1)
    for i, command in enumerate(commands):
        if command.startswith("put "):
            for smaller in int_candidates(0, 9, int(command[4:])):
                found.append(commands[:i] + [f"put {smaller}"] + commands[i + 1 :])
    seen = {", ".join(commands)}
    kept = []
    for candidate in found:
        key = ", ".join(candidate)
        if key not in seen and valid(capacity, candidate):
            seen.add(key)
            kept.append(candidate)
    return kept


class PropertyRunner:
    """Generators are prefix token lists parsed into nested tuples. One xorshift32 stream feeds
    a whole call, so every value is fixed by the seed and its position. Shrinking is greedy: from
    the failing value, take the first candidate that still fails, and start again from it, until
    no candidate fails. Candidates are built from the generator, so each one is a value the
    generator could have drawn: in range, long enough and through every filter. The stateful
    level runs each command sequence on the correct queue and on the buggy one and shrinks the
    sequence the same way, keeping only sequences whose commands are all allowed.
    """

    def __init__(self) -> None:
        self._limit = 100

    # Level 1
    def randoms(self, seed: int, count: int) -> list[int]:
        rng = Random(seed, self._limit)
        return [rng.next() for _ in range(count)]

    def generate(self, gen: str, seed: int, count: int) -> list[str]:
        rng = Random(seed, self._limit)
        values = []
        try:
            for _ in range(count):
                values.append(text(draw(generator(gen), rng)))
        except GiveUp:
            pass
        return values

    def check(self, gen: str, prop: str, seed: int, runs: int) -> str:
        outcome, run, value = self._search(gen, prop, seed, runs)
        if outcome == "failed":
            return f"failed {run}: {text(value)}"
        if outcome == "gave up":
            return f"gave up after {run}"
        return f"passed {runs}"

    # Level 2
    def candidates(self, gen: str, seed: int, index: int) -> list[str]:
        rng = Random(seed, self._limit)
        parsed = generator(gen)
        try:
            for _ in range(index - 1):
                draw(parsed, rng)
            value = draw(parsed, rng)
        except GiveUp:
            return []
        return [text(candidate) for candidate in candidates_of(parsed, value)]

    def minimize(self, gen: str, prop: str, seed: int, runs: int) -> list[str]:
        outcome, _, value = self._search(gen, prop, seed, runs)
        if outcome != "failed":
            return []
        parsed = generator(gen)
        path = [text(value)]
        while True:
            smaller = next((c for c in candidates_of(parsed, value) if not holds(prop, c)), None)
            if smaller is None:
                return path
            value = smaller
            path.append(text(value))

    # Level 3
    def set_discard_limit(self, limit: int) -> None:
        self._limit = limit

    # Level 4
    def replay(self, capacity: int, bug: str, commands: list[str]) -> list[str]:
        model, system = Queue(capacity, "none"), Queue(capacity, bug)
        answers = []
        for command in commands:
            if not model.allows(command):
                answers.append("invalid")
                break
            model.apply(command)
            answers.append(system.apply(command))
        return answers

    def generate_commands(self, capacity: int, seed: int, count: int, max_length: int) -> list[str]:
        rng = Random(seed, self._limit)
        return [", ".join(sequence(capacity, rng, max_length)) for _ in range(count)]

    def first_failure(
        self, capacity: int, bug: str, seed: int, runs: int, max_length: int
    ) -> list[str]:
        rng = Random(seed, self._limit)
        for _ in range(runs):
            commands = sequence(capacity, rng, max_length)
            if fails(capacity, bug, commands):
                return commands
        return []

    def shrink_failure(
        self, capacity: int, bug: str, seed: int, runs: int, max_length: int
    ) -> list[str]:
        commands = self.first_failure(capacity, bug, seed, runs, max_length)
        while commands:
            smaller = next(
                (c for c in sequence_candidates(capacity, commands) if fails(capacity, bug, c)),
                None,
            )
            if smaller is None:
                break
            commands = smaller
        return commands

    def _search(self, gen: str, prop: str, seed: int, runs: int):
        rng = Random(seed, self._limit)
        parsed = generator(gen)
        passed = 0
        try:
            for run in range(1, runs + 1):
                value = draw(parsed, rng)
                if not holds(prop, value):
                    return "failed", run, value
                passed += 1
        except GiveUp:
            return "gave up", passed, None
        return "passed", runs, None
