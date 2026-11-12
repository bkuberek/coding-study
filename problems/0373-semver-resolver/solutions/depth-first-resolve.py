import re
from dataclasses import dataclass, field

NUMBER = re.compile(r"0|[1-9][0-9]*")
IDENTIFIER = re.compile(r"[0-9A-Za-z-]+")
WILDCARDS = ("x", "X", "*")
OPERATORS = (">=", "<=", ">", "<", "=", "^", "~")


@dataclass(frozen=True)
class Version:
    """A parsed version without its build metadata. `key` orders versions by precedence."""

    major: int
    minor: int
    patch: int
    pre: tuple[str, ...]

    @property
    def key(self) -> tuple:
        identifiers = tuple((0, int(p), "") if p.isdigit() else (1, 0, p) for p in self.pre)
        return (self.major, self.minor, self.patch, 0 if self.pre else 1, identifiers)

    def text(self) -> str:
        core = f"{self.major}.{self.minor}.{self.patch}"
        return core + ("-" + ".".join(self.pre) if self.pre else "")


def parse(text: str) -> Version | None:
    """A version as SemVer 2.0.0 writes it, or None."""
    rest, plus, build = text.partition("+")
    if plus and not all(IDENTIFIER.fullmatch(part) for part in build.split(".")):
        return None
    core, dash, pre = rest.partition("-")
    numbers = core.split(".")
    if len(numbers) != 3 or not all(NUMBER.fullmatch(n) for n in numbers):
        return None
    parts = pre.split(".") if dash else []
    for part in parts:
        if not IDENTIFIER.fullmatch(part) or (part.isdigit() and not NUMBER.fullmatch(part)):
            return None
    return Version(int(numbers[0]), int(numbers[1]), int(numbers[2]), tuple(parts))


def order(first: Version, second: Version) -> int:
    return (first.key > second.key) - (first.key < second.key)


Comparator = tuple[str, Version]
ComparatorSet = list[Comparator]


def partial(pattern: str) -> list[int] | None:
    """The leading numbers of a pattern such as `1`, `1.x` or `1.2.*`, or None."""
    parts = pattern.split(".")
    if len(parts) > 3:
        return None
    numbers: list[int] = []
    for i, part in enumerate(parts):
        if part in WILDCARDS:
            return numbers if all(rest in WILDCARDS for rest in parts[i:]) else None
        if not NUMBER.fullmatch(part):
            return None
        numbers.append(int(part))
    return numbers if len(numbers) < 3 else None


def floor_of(numbers: list[int]) -> Version:
    padded = numbers + [0] * (3 - len(numbers))
    return Version(padded[0], padded[1], padded[2], ())


def below(major: int, minor: int, patch: int) -> Comparator:
    """`<M.m.p-0`: under every version of M.m.p, pre-releases included."""
    return ("<", Version(major, minor, patch, ("0",)))


def wildcard_range(numbers: list[int]) -> ComparatorSet:
    if not numbers:
        return [(">=", Version(0, 0, 0, ()))]
    if len(numbers) == 1:
        return [(">=", floor_of(numbers)), below(numbers[0] + 1, 0, 0)]
    return [(">=", floor_of(numbers)), below(numbers[0], numbers[1] + 1, 0)]


def caret_upper(numbers: list[int]) -> Comparator:
    major, minor, patch = numbers + [0] * (3 - len(numbers))
    if major > 0 or len(numbers) == 1:
        return below(major + 1, 0, 0)
    if minor > 0 or len(numbers) == 2:
        return below(0, minor + 1, 0)
    return below(0, 0, patch + 1)


def expand_term(term: str) -> ComparatorSet | None:
    operator = next((op for op in OPERATORS if term.startswith(op)), "")
    pattern = term[len(operator) :]
    full = parse(pattern)
    if full is not None:
        if operator in ("", "="):
            return [("=", full)]
        if operator == "~":
            return [(">=", full), below(full.major, full.minor + 1, 0)]
        if operator == "^":
            return [(">=", full), caret_upper([full.major, full.minor, full.patch])]
        return [(operator, full)]
    numbers = partial(pattern)
    if numbers is None or operator not in ("", "=", "^", "~"):
        return None
    if operator == "^" and numbers:
        return [(">=", floor_of(numbers)), caret_upper(numbers)]
    return wildcard_range(numbers)


def expand(text: str) -> list[ComparatorSet] | None:
    sets: list[ComparatorSet] = []
    for piece in text.split("||"):
        terms = [term for term in piece.split(" ") if term]
        if not terms:
            return None
        comparators: ComparatorSet = []
        for term in terms:
            expanded = expand_term(term)
            if expanded is None:
                return None
            comparators.extend(expanded)
        sets.append(comparators)
    return sets


def holds(version: Version, comparator: Comparator) -> bool:
    operator, bound = comparator
    sign = order(version, bound)
    return {
        "=": sign == 0,
        ">": sign > 0,
        ">=": sign >= 0,
        "<": sign < 0,
        "<=": sign <= 0,
    }[operator]


def in_set(version: Version, comparators: ComparatorSet) -> bool:
    if not all(holds(version, c) for c in comparators):
        return False
    if not version.pre:
        return True
    core = (version.major, version.minor, version.patch)
    return any(b.pre and (b.major, b.minor, b.patch) == core for _, b in comparators)


def in_range(version: Version, sets: list[ComparatorSet]) -> bool:
    return any(in_set(version, comparators) for comparators in sets)


@dataclass
class Release:
    name: str
    text: str
    version: Version
    dependencies: list[tuple[str, str, list[ComparatorSet], int]] = field(default_factory=list)
    """(package, range text, expanded range, constraint number)"""


class SemverResolver:
    """Versions are parsed once into a precedence key; ranges are expanded into comparator sets.
    Resolving is a depth-first search that picks the smallest open package name and tries its
    versions from the highest down, undoing a choice when the rest cannot be resolved. Explaining
    a failure reruns the search with constraints left out, one at a time.
    """

    def __init__(self) -> None:
        self._releases: dict[str, list[Release]] = {}
        self._published: list[Release] = []
        self._edges = 0

    # Level 1
    def is_valid(self, version: str) -> bool:
        return parse(version) is not None

    def compare(self, first: str, second: str) -> int:
        a, b = parse(first), parse(second)
        assert a is not None and b is not None
        return order(a, b)

    def sort_versions(self, versions: list[str]) -> list[str]:
        valid = [(parse(text), text) for text in versions]
        return [text for v, text in sorted((v.key, text) for v, text in valid if v is not None)]

    def change_kind(self, before: str, after: str) -> str:
        old, new = parse(before), parse(after)
        if old is None or new is None:
            return "invalid"
        sign = order(new, old)
        if sign < 0:
            return "downgrade"
        if sign == 0:
            return "none"
        if new.major != old.major:
            return "major"
        if new.minor != old.minor:
            return "minor"
        if new.patch != old.patch:
            return "patch"
        return "pre-release"

    # Level 2
    def expand_range(self, version_range: str) -> list[str]:
        sets = expand(version_range)
        if sets is None:
            return []
        return [" ".join(op + bound.text() for op, bound in comparators) for comparators in sets]

    def satisfies(self, version: str, version_range: str) -> bool:
        parsed, sets = parse(version), expand(version_range)
        return parsed is not None and sets is not None and in_range(parsed, sets)

    def max_satisfying(self, versions: list[str], version_range: str) -> str:
        sets = expand(version_range)
        if sets is None:
            return ""
        best: tuple | None = None
        for text in versions:
            parsed = parse(text)
            if parsed is not None and in_range(parsed, sets):
                best = max(best, (parsed.key, text)) if best else (parsed.key, text)
        return best[1] if best else ""

    # Level 3
    def publish(self, name: str, version: str, dependencies: list[list[str]]) -> str:
        parsed = parse(version)
        if parsed is None:
            return "invalid-version"
        releases = self._releases.setdefault(name, [])
        if any(order(r.version, parsed) == 0 for r in releases):
            return "duplicate"
        names = [package for package, _ in dependencies]
        expanded = [expand(text) for _, text in dependencies]
        if len(set(names)) != len(names) or name in names or None in expanded:
            return "invalid-dependency"
        release = Release(name, version, parsed)
        for (package, text), sets in zip(dependencies, expanded, strict=True):
            assert sets is not None
            release.dependencies.append((package, text, sets, self._edges))
            self._edges += 1
        releases.append(release)
        releases.sort(key=lambda r: r.version.key, reverse=True)
        self._published.append(release)
        return "ok"

    def candidates(self, name: str, version_range: str) -> list[str]:
        sets = expand(version_range)
        if sets is None:
            return []
        return [r.text for r in self._releases.get(name, []) if in_range(r.version, sets)]

    def resolve(self, requirements: list[list[str]]) -> list[str]:
        return self._result(self._search(self._roots(requirements), set(), set(), {}))

    # Level 4
    def explain(self, requirements: list[list[str]]) -> list[str]:
        roots = self._roots(requirements)
        if self._search(roots, set(), set(), {}) is not None:
            return []
        lines = [(("root", i), f"root requires {name} {text}") for i, (name, text, _) in enumerate(roots)]
        for release in self._published:
            for package, text, _, edge in release.dependencies:
                lines.append((("edge", edge), f"{release.name}@{release.text} requires {package} {text}"))
        dropped_roots: set[int] = set()
        dropped_edges: set[int] = set()
        kept = []
        for (kind, number), line in lines:
            dropped = dropped_roots if kind == "root" else dropped_edges
            dropped.add(number)
            if self._search(roots, dropped_roots, dropped_edges, {}) is not None:
                dropped.discard(number)
                kept.append(line)
        return kept

    def locked_resolve(self, requirements: list[list[str]], lock: list[str]) -> list[str]:
        return self._result(self._search(self._roots(requirements), set(), set(), self._lock(lock)))

    def update(self, requirements: list[list[str]], lock: list[str], unlock: list[str]) -> list[str]:
        before = self._lock(lock)
        preferred = {name: text for name, text in before.items() if name not in unlock}
        chosen = self._search(self._roots(requirements), set(), set(), preferred)
        if chosen is None:
            return ["unsatisfiable"]
        after = {name: release.text for name, release in chosen.items()}
        changes = []
        for name in sorted(before.keys() | after.keys()):
            old, new = before.get(name), after.get(name)
            if old is None:
                changes.append(f"{name}: added {new}")
            elif new is None:
                changes.append(f"{name}: removed {old}")
            elif old != new:
                changes.append(f"{name}: {old} -> {new} ({self.change_kind(old, new)})")
        return changes

    # Helpers
    def _roots(self, requirements: list[list[str]]) -> list[tuple[str, str, list[ComparatorSet]]]:
        roots = []
        for name, text in requirements:
            sets = expand(text)
            assert sets is not None
            roots.append((name, text, sets))
        return roots

    @staticmethod
    def _lock(lock: list[str]) -> dict[str, str]:
        return dict(entry.split("@", 1) for entry in lock)  # type: ignore[misc]

    @staticmethod
    def _result(chosen: dict[str, Release] | None) -> list[str]:
        if chosen is None:
            return []
        return [f"{name}@{chosen[name].text}" for name in sorted(chosen)]

    def _search(
        self,
        roots: list[tuple[str, str, list[ComparatorSet]]],
        dropped_roots: set[int],
        dropped_edges: set[int],
        preferred: dict[str, str],
    ) -> dict[str, Release] | None:
        """The chosen release of every needed package, or None when the constraints in force
        cannot all hold."""
        root_ranges = [(name, sets) for i, (name, _, sets) in enumerate(roots) if i not in dropped_roots]
        chosen: dict[str, Release] = {}

        def in_force(release: Release) -> list[tuple[str, list[ComparatorSet]]]:
            return [(p, sets) for p, _, sets, edge in release.dependencies if edge not in dropped_edges]

        def ranges_on(name: str) -> list[list[ComparatorSet]]:
            found = [sets for package, sets in root_ranges if package == name]
            for release in chosen.values():
                found.extend(sets for package, sets in in_force(release) if package == name)
            return found

        def tries(name: str) -> list[Release]:
            releases = self._releases.get(name, [])
            first = [r for r in releases if r.text == preferred.get(name)]
            return first + [r for r in releases if r.text != preferred.get(name)]

        def solve() -> bool:
            needed = {name for name, _ in root_ranges}
            for release in chosen.values():
                needed.update(package for package, _ in in_force(release))
            open_names = sorted(needed - chosen.keys())
            if not open_names:
                return True
            name = open_names[0]
            ranges = ranges_on(name)
            for release in tries(name):
                if not all(in_range(release.version, sets) for sets in ranges):
                    continue
                if any(
                    package in chosen and not in_range(chosen[package].version, sets)
                    for package, sets in in_force(release)
                ):
                    continue
                chosen[name] = release
                if solve():
                    return True
                del chosen[name]
            return False

        return dict(chosen) if solve() else None
