import heapq

UNKNOWN = "!unknown"
UNEXPECTED = "!unexpected"


def fits(pattern: list[str], args: list[str]) -> bool:
    """A pattern fits arguments of the same length whose values equal it, `*` fitting any."""
    return len(pattern) == len(args) and all(p in ("*", a) for p, a in zip(pattern, args))


class Rule:
    def __init__(self, pattern: list[str], answers: list[str]) -> None:
        self.pattern = pattern
        self.answers = answers
        self.used = 0

    def next_answer(self) -> str:
        answer = self.answers[min(self.used, len(self.answers) - 1)]
        self.used += 1
        return answer


class Expectation:
    def __init__(self, method: str, pattern: list[str], answer: str, times: int) -> None:
        self.method = method
        self.pattern = pattern
        self.answer = answer
        self.times = times
        self.used = 0


class Double:
    def __init__(self, name: str, mock: bool, strict: bool) -> None:
        self.name = name
        self.mock = mock
        self.strict = strict
        self.rules: dict[str, list[Rule]] = {}
        self.fallback: dict[str, str] = {}
        self.expectations: list[Expectation] = []
        self.unexpected: list[tuple[str, list[str]]] = []
        self.calls: list[int] = []

    def answer(self, method: str, args: list[str]) -> str:
        for expectation in self.expectations:
            if (
                expectation.method == method
                and expectation.used < expectation.times
                and fits(expectation.pattern, args)
            ):
                expectation.used += 1
                return expectation.answer
        for rule in reversed(self.rules.get(method, [])):
            if fits(rule.pattern, args):
                return rule.next_answer()
        if method in self.fallback:
            return self.fallback[method]
        if not self.mock:
            return ""
        self.unexpected.append((method, args))
        return UNEXPECTED if self.strict else ""


class Doubles:
    """Every double keeps its stub rules per method, newest last, and a mock also keeps its
    expectations in the order they were set. One log holds every call in the order it was made,
    with its time, and each double keeps the positions of its own calls in that log, so the spy
    questions read short lists. Timers wait in a heap ordered by due time, then by the sequence
    number they got when they were last put in, so equal times fire in scheduling order.
    """

    def __init__(self) -> None:
        self._doubles: dict[str, Double] = {}
        self._log: list[tuple[str, str, list[str], int]] = []
        self._now = 0
        self._heap: list[tuple[int, int, int]] = []
        self._timers: dict[int, list] = {}
        self._sequence = 0

    # Level 1
    def add_stub(self, name: str) -> bool:
        return self._add(name, False, False)

    def on_call(self, name: str, method: str, args: list[str], answers: list[str]) -> bool:
        double = self._doubles.get(name)
        if double is None:
            return False
        double.rules.setdefault(method, []).append(Rule(list(args), list(answers)))
        return True

    def otherwise(self, name: str, method: str, answer: str) -> bool:
        double = self._doubles.get(name)
        if double is None:
            return False
        double.fallback[method] = answer
        return True

    def call(self, name: str, method: str, args: list[str]) -> str:
        double = self._doubles.get(name)
        if double is None:
            return UNKNOWN
        double.calls.append(len(self._log))
        self._log.append((name, method, list(args), self._now))
        return double.answer(method, list(args))

    # Level 2
    def call_count(self, name: str, method: str) -> int:
        return self._count(name, method, None)

    def match_count(self, name: str, method: str, args: list[str]) -> int:
        return self._count(name, method, args)

    def nth_call(self, name: str, n: int) -> list[str]:
        double = self._doubles.get(name)
        if double is None or n == 0 or abs(n) > len(double.calls):
            return []
        _, method, args, _ = self._log[double.calls[n - 1 if n > 0 else n]]
        return [method, *args]

    def in_order(self, steps: list[list[str]]) -> bool:
        step = 0
        for name, method, args, _ in self._log:
            if step == len(steps):
                break
            wanted = steps[step]
            if wanted[0] == name and wanted[1] == method and fits(wanted[2:], args):
                step += 1
        return step == len(steps)

    # Level 3
    def add_mock(self, name: str, strict: bool) -> bool:
        return self._add(name, True, strict)

    def expect(self, name: str, method: str, args: list[str], answer: str, times: int) -> bool:
        double = self._doubles.get(name)
        if double is None or not double.mock:
            return False
        double.expectations.append(Expectation(method, list(args), answer, times))
        return True

    def verify(self, name: str) -> list[str]:
        double = self._doubles.get(name)
        if double is None:
            return [UNKNOWN]
        report = [
            f"missing {name}.{e.method}({','.join(e.pattern)}) {e.used}/{e.times}"
            for e in double.expectations
            if e.used < e.times
        ]
        report += [
            f"unexpected {name}.{method}({','.join(args)})" for method, args in double.unexpected
        ]
        return report

    def verify_all(self) -> list[str]:
        return [line for name, d in self._doubles.items() if d.mock for line in self.verify(name)]

    # Level 4
    def now(self) -> int:
        return self._now

    def schedule(self, delay: int, name: str, method: str, args: list[str]) -> int:
        return self._timer(delay, 0, name, method, args)

    def every(self, interval: int, name: str, method: str, args: list[str]) -> int:
        return self._timer(interval, interval, name, method, args)

    def cancel(self, timer_id: int) -> bool:
        timer = self._timers.get(timer_id)
        if timer is None or timer[4]:
            return False
        timer[4] = True
        return True

    def advance(self, ms: int) -> list[str]:
        end = self._now + ms
        fired = []
        while self._heap and self._heap[0][0] <= end:
            due, _, timer_id = heapq.heappop(self._heap)
            name, method, args, interval, stopped = self._timers[timer_id]
            if stopped:
                continue
            self._now = due
            if interval > 0:
                self._push(due + interval, timer_id)
            else:
                self._timers[timer_id][4] = True
            fired.append(f"{timer_id}@{due}")
            self.call(name, method, args)
        self._now = end
        return fired

    def pending(self) -> list[str]:
        live = sorted(entry for entry in self._heap if not self._timers[entry[2]][4])
        return [f"{timer_id}@{due}" for due, _, timer_id in live]

    def call_times(self, name: str, method: str) -> list[int]:
        double = self._doubles.get(name)
        if double is None:
            return []
        return [self._log[p][3] for p in double.calls if self._log[p][1] == method]

    def _count(self, name: str, method: str, pattern: list[str] | None) -> int:
        double = self._doubles.get(name)
        if double is None:
            return -1
        return sum(
            1
            for position in double.calls
            if self._log[position][1] == method
            and (pattern is None or fits(pattern, self._log[position][2]))
        )

    def _add(self, name: str, mock: bool, strict: bool) -> bool:
        if name in self._doubles:
            return False
        self._doubles[name] = Double(name, mock, strict)
        return True

    def _timer(self, delay: int, interval: int, name: str, method: str, args: list[str]) -> int:
        if name not in self._doubles:
            return -1
        timer_id = len(self._timers) + 1
        self._timers[timer_id] = [name, method, list(args), interval, False]
        self._push(self._now + delay, timer_id)
        return timer_id

    def _push(self, due: int, timer_id: int) -> None:
        self._sequence += 1
        heapq.heappush(self._heap, (due, self._sequence, timer_id))
