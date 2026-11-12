class PatternError(Exception):
    def __init__(self, code: str, position: int) -> None:
        super().__init__(code)
        self.code = code
        self.position = position


REPEATS = {"*": "star", "+": "plus", "?": "opt"}


class Parser:
    """Recursive descent over the grammar alternation > concatenation > repetition > atom. A
    pattern has at most 100 characters, so the recursion is at most about 300 frames deep."""

    def __init__(self, pattern: str) -> None:
        self.text = pattern
        self.pos = 0

    def peek(self) -> str:
        return self.text[self.pos] if self.pos < len(self.text) else ""

    def parse(self) -> tuple:
        node = self.alternation()
        if self.pos < len(self.text):
            raise PatternError("unmatched-paren", self.pos)
        return node

    def alternation(self) -> tuple:
        branches = [self.sequence()]
        while self.peek() == "|":
            self.pos += 1
            branches.append(self.sequence())
        return branches[0] if len(branches) == 1 else ("alt", branches)

    def sequence(self) -> tuple:
        items = []
        while self.peek() not in ("", "|", ")"):
            items.append(self.repetition())
        if not items:
            return ("empty",)
        return items[0] if len(items) == 1 else ("cat", items)

    def repetition(self) -> tuple:
        if self.peek() in REPEATS:
            raise PatternError("nothing-to-repeat", self.pos)
        node = self.atom()
        while self.peek() in REPEATS:
            node = (REPEATS[self.peek()], node)
            self.pos += 1
        return node

    def atom(self) -> tuple:
        start = self.pos
        char = self.peek()
        self.pos += 1
        if char == "(":
            inner = self.alternation()
            if self.peek() != ")":
                raise PatternError("unclosed-group", start)
            self.pos += 1
            return inner
        if char == ".":
            return ("any",)
        if char == "[":
            return self.char_class(start)
        return ("lit", char)

    def char_class(self, start: int) -> tuple:
        negated = self.peek() == "^"
        if negated:
            self.pos += 1
        items: list[tuple[str, str]] = []
        while True:
            if self.pos >= len(self.text):
                raise PatternError("unclosed-class", start)
            if self.peek() == "]":
                if not items:
                    raise PatternError("empty-class", start)
                self.pos += 1
                return ("class", negated, items)
            low_at = self.pos
            low = self.text[low_at]
            self.pos += 1
            is_range = (
                self.peek() == "-" and self.pos + 1 < len(self.text) and self.text[self.pos + 1] != "]"
            )
            if is_range:
                high = self.text[self.pos + 1]
                if high < low:
                    raise PatternError("bad-range", low_at)
                self.pos += 2
                items.append((low, high))
            else:
                items.append((low, low))


def show_class(node: tuple) -> str:
    _, negated, items = node
    parts = [f"'{low}'" if low == high else f"'{low}'-'{high}'" for low, high in items]
    return ("notclass(" if negated else "class(") + ",".join(parts) + ")"


def show(node: tuple) -> str:
    kind = node[0]
    if kind == "lit":
        return f"'{node[1]}'"
    if kind in ("any", "empty"):
        return kind
    if kind == "class":
        return show_class(node)
    if kind in ("cat", "alt"):
        return kind + "(" + ",".join(show(child) for child in node[1]) + ")"
    return kind + "(" + show(node[1]) + ")"


class Machine:
    """States in the order they are created; `outs[i]` lists the arrows of state `i`, and a hole is
    an arrow still set to None, written as the pair (state, arrow index)."""

    def __init__(self) -> None:
        self.kind: list[str] = []
        self.label: list[tuple | None] = []
        self.outs: list[list[int | None]] = []

    def add(self, kind: str, label: tuple | None, arrows: int) -> int:
        self.kind.append(kind)
        self.label.append(label)
        self.outs.append([None] * arrows)
        return len(self.kind) - 1

    def patch(self, holes: list[tuple[int, int]], target: int) -> None:
        for state, index in holes:
            self.outs[state][index] = target

    def fragment(self, node: tuple) -> tuple[int, list[tuple[int, int]]]:
        kind = node[0]
        if kind in ("lit", "any", "empty", "class"):
            state = self.add("char" if kind == "lit" else kind, node, 1)
            return state, [(state, 0)]
        if kind == "cat":
            start, holes = self.fragment(node[1][0])
            for child in node[1][1:]:
                child_start, child_holes = self.fragment(child)
                self.patch(holes, child_start)
                holes = child_holes
            return start, holes
        if kind == "alt":
            split = self.add("split", None, len(node[1]))
            holes = []
            for index, child in enumerate(node[1]):
                child_start, child_holes = self.fragment(child)
                self.outs[split][index] = child_start
                holes += child_holes
            return split, holes
        inner_start, inner_holes = self.fragment(node[1])
        split = self.add("split", None, 2)
        self.outs[split][0] = inner_start
        if kind == "star":
            self.patch(inner_holes, split)
            return split, [(split, 1)]
        if kind == "plus":
            self.patch(inner_holes, split)
            return inner_start, [(split, 1)]
        return split, inner_holes + [(split, 1)]


class Automaton:
    """The machine renumbered breadth first from its start state, which is what `nfa` prints."""

    def __init__(self, node: tuple) -> None:
        machine = Machine()
        start, holes = machine.fragment(node)
        machine.patch(holes, machine.add("match", None, 0))
        number = {start: 0}
        order = [start]
        for state in order:
            for target in machine.outs[state]:
                if target not in number:
                    number[target] = len(order)
                    order.append(target)
        self.kind = [machine.kind[state] for state in order]
        self.label = [machine.label[state] for state in order]
        self.outs = [[number[t] for t in machine.outs[state]] for state in order]
        self.final = self.kind.index("match")

    def line(self, state: int) -> str:
        kind = self.kind[state]
        head = f"{state}: "
        if kind == "char":
            head += f"char '{self.label[state][1]}'"
        elif kind == "class":
            head += show_class(self.label[state])
        else:
            head += kind
        if not self.outs[state]:
            return head
        return head + " -> " + ", ".join(str(target) for target in self.outs[state])

    def accepts(self, state: int, char: str) -> bool:
        kind = self.kind[state]
        if kind == "char":
            return self.label[state][1] == char
        if kind == "any":
            return True
        if kind == "class":
            _, negated, items = self.label[state]
            inside = any(low <= char <= high for low, high in items)
            return inside != negated
        return False

    def closure(self, sources: list[int]) -> list[int]:
        """Every state reachable from the sources through split and empty arrows, the sources
        included, in the order they are first reached."""
        seen = set()
        reached = []
        stack = list(reversed(sources))
        while stack:
            state = stack.pop()
            if state in seen:
                continue
            seen.add(state)
            reached.append(state)
            if self.kind[state] in ("split", "empty"):
                stack.extend(reversed(self.outs[state]))
        return reached

    def advance(self, current: list[int], char: str) -> list[int]:
        return self.closure([self.outs[s][0] for s in current if self.accepts(s, char)])

    def run(self, text: str) -> tuple[bool, int]:
        current = self.closure([0])
        steps = len(current)
        for char in text:
            current = self.advance(current, char)
            steps += len(current)
            if not current:
                return False, steps
        return self.final in current, steps

    def leftmost_longest(self, text: str) -> list[int]:
        """One pass over the text. Each live state carries the earliest start that reaches it, and
        the live list stays ordered by start, because new starts are appended at the end and a
        step visits the list in order, so the first path to reach a state has the earliest start.
        Once a match is seen, later starts are dropped and the scan goes on only while a state
        with that start or an earlier one is alive."""
        best: tuple[int, int] | None = None
        live: list[tuple[int, int]] = []
        for position in range(len(text) + 1):
            if best is None:
                have = {state for state, _ in live}
                live += [(state, position) for state in self.closure([0]) if state not in have]
            for state, start in live:
                if state == self.final and (best is None or start <= best[0]):
                    best = (start, position)
            if best is not None:
                live = [(state, start) for state, start in live if start <= best[0]]
            if position == len(text) or not live:
                break
            seen: set[int] = set()
            moved: list[tuple[int, int]] = []
            for state, start in live:
                if self.accepts(state, text[position]):
                    for reached in self.closure([self.outs[state][0]]):
                        if reached not in seen:
                            seen.add(reached)
                            moved.append((reached, start))
            live = moved
        return [-1, -1] if best is None else list(best)


class RegexEngine:
    """A recursive-descent parser builds the syntax tree; Thompson's construction turns it into
    an automaton with one state per character, class or operator; matching runs every live state
    in step with the text, so it never backtracks. Compiled automata are cached by pattern."""

    def __init__(self) -> None:
        self._automata: dict[str, Automaton] = {}

    def _automaton(self, pattern: str) -> Automaton:
        if pattern not in self._automata:
            self._automata[pattern] = Automaton(Parser(pattern).parse())
        return self._automata[pattern]

    # Level 1
    def parse(self, pattern: str) -> str:
        try:
            return show(Parser(pattern).parse())
        except PatternError as error:
            return f"error: {error.code} at {error.position}"

    # Level 2
    def nfa(self, pattern: str) -> list[str]:
        automaton = self._automaton(pattern)
        return [automaton.line(state) for state in range(len(automaton.kind))]

    # Level 3
    def full_match(self, pattern: str, text: str) -> bool:
        return self._automaton(pattern).run(text)[0]

    def count_steps(self, pattern: str, text: str) -> int:
        return self._automaton(pattern).run(text)[1]

    # Level 4
    def search(self, pattern: str, text: str) -> list[int]:
        return self._automaton(pattern).leftmost_longest(text)
