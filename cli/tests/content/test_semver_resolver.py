"""semver-resolver promises that its hidden cases catch the classic mistakes of working with
semantic versions: precedence read as text or with the build metadata, pre-release identifiers
ordered the wrong way, caret and tilde ranges expanded as if 0.x were stable, pre-releases let
into every range, a resolver that never backtracks or keeps the requirements of a choice it undid,
and an explanation or a lockfile update that says the wrong thing. These tests replay every case
against a model of the resolver written from the statement, which must give every expected
output, and against that model with one mistake planted at a time, which some hidden case must
fail. A mistake that crashes fails its case, as a thrown exception does in the grader."""

import json
import re
from collections.abc import Mapping, Sequence
from functools import cmp_to_key
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0373-semver-resolver"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]

LOWEST = ("0",)


class Model:
    """The resolver as the statement words it. A version is a tuple (major, minor, patch, pre),
    with pre a tuple of identifier strings; a comparator is (operator, version). Each mistake
    below overrides one rule."""

    def __init__(self) -> None:
        self.registry: dict[str, list[tuple[str, tuple, list[tuple[str, str]]]]] = {}
        self.history: list[tuple[str, str, list[tuple[str, str]]]] = []

    # --- versions
    def number_ok(self, text: str) -> bool:
        return re.fullmatch(r"0|[1-9]\d*", text) is not None

    def pre_ok(self, text: str) -> bool:
        if not re.fullmatch(r"[0-9A-Za-z-]+", text):
            return False
        return not text.isdigit() or self.number_ok(text)

    def build_ok(self, text: str) -> bool:
        return re.fullmatch(r"[0-9A-Za-z-]+", text) is not None

    def parse(self, text: str) -> tuple | None:
        match = re.fullmatch(r"([^-+]*)(?:-([^+]*))?(?:\+(.*))?", text)
        if match is None:
            return None
        core, pre, build = match.groups()
        numbers = core.split(".")
        if len(numbers) != 3 or not all(self.number_ok(n) for n in numbers):
            return None
        pres = tuple(pre.split(".")) if pre is not None else ()
        if not all(self.pre_ok(p) for p in pres):
            return None
        if build is not None and not all(self.build_ok(b) for b in build.split(".")):
            return None
        return (int(numbers[0]), int(numbers[1]), int(numbers[2]), pres, build)

    def compare_identifiers(self, a: str, b: str) -> int:
        if a.isdigit() and b.isdigit():
            return (int(a) > int(b)) - (int(a) < int(b))
        if a.isdigit() != b.isdigit():
            return -1 if a.isdigit() else 1
        return (a > b) - (a < b)

    def compare_pre(self, a: tuple, b: tuple) -> int:
        if not a or not b:
            return (not a) - (not b)
        for x, y in zip(a, b, strict=False):
            if (sign := self.compare_identifiers(x, y)) != 0:
                return sign
        return (len(a) > len(b)) - (len(a) < len(b))

    def compare_parsed(self, a: tuple, b: tuple) -> int:
        if a[:3] != b[:3]:
            return (a[:3] > b[:3]) - (a[:3] < b[:3])
        return self.compare_pre(a[3], b[3])

    def is_valid(self, version: str) -> bool:
        return self.parse(version) is not None

    def compare(self, first: str, second: str) -> int:
        a, b = self.parse(first), self.parse(second)
        assert a is not None
        assert b is not None
        return self.compare_parsed(a, b)

    def sort_versions(self, versions: list[str]) -> list[str]:
        valid = [v for v in versions if self.parse(v) is not None]

        def by(x: str, y: str) -> int:
            return self.compare(x, y) or (x > y) - (x < y)

        return sorted(valid, key=cmp_to_key(by))

    def change_kind(self, before: str, after: str) -> str:
        a, b = self.parse(before), self.parse(after)
        if a is None or b is None:
            return "invalid"
        sign = self.compare_parsed(b, a)
        if sign < 0:
            return "downgrade"
        if sign == 0:
            return "none"
        for index, word in enumerate(("major", "minor", "patch")):
            if a[index] != b[index]:
                return word
        return "pre-release"

    # --- ranges
    def write(self, version: tuple) -> str:
        text = f"{version[0]}.{version[1]}.{version[2]}"
        return text + ("-" + ".".join(version[3]) if version[3] else "")

    def caret_top(self, numbers: list[int], full: bool) -> tuple:
        major, minor, patch = ([*numbers, 0, 0])[:3]
        if major > 0 or len(numbers) == 1:
            return (major + 1, 0, 0, LOWEST)
        if minor > 0 or not full:
            return (0, minor + 1, 0, LOWEST)
        return (0, 0, patch + 1, LOWEST)

    def tilde_top(self, numbers: list[int]) -> tuple:
        if len(numbers) == 1:
            return (numbers[0] + 1, 0, 0, LOWEST)
        return (numbers[0], numbers[1] + 1, 0, LOWEST)

    def wildcard_numbers(self, pattern: str) -> list[int] | None:
        parts = pattern.split(".")
        if not 1 <= len(parts) <= 3:
            return None
        numbers: list[int] = []
        for i, part in enumerate(parts):
            if part in ("x", "X", "*"):
                if all(p in ("x", "X", "*") for p in parts[i:]):
                    return numbers
                return None
            if not self.number_ok(part):
                return None
            numbers.append(int(part))
        return numbers if len(numbers) < 3 else None

    def partial_allowed(self, op: str) -> bool:
        return op in ("", "=", "^", "~")

    def term(self, text: str) -> list[tuple[str, tuple]] | None:
        op = re.match(r"(>=|<=|>|<|=|\^|~)?", text).group(0)  # type: ignore[union-attr]
        pattern = text[len(op) :]
        full = self.parse(pattern)
        if full is not None:
            version = full[:4]
            if op in ("", "="):
                return [("=", version)]
            if op == "^":
                return [(">=", version), ("<", self.caret_top(list(version[:3]), True))]
            if op == "~":
                return [(">=", version), ("<", self.tilde_top(list(version[:2])))]
            return [(op, version)]
        numbers = self.wildcard_numbers(pattern)
        if numbers is None or not self.partial_allowed(op):
            return None
        if not numbers:
            return [(">=", (0, 0, 0, ()))]
        low = (*([*numbers, 0, 0])[:3], ())
        if op == "^":
            return [(">=", low), ("<", self.caret_top(numbers, False))]
        return [(">=", low), ("<", self.tilde_top(numbers))]

    def pieces(self, text: str) -> list[str]:
        return text.split("||")

    def sets(self, text: str) -> list[list[tuple[str, tuple]]] | None:
        found = []
        for piece in self.pieces(text):
            words = [w for w in piece.split(" ") if w]
            if not words:
                return None
            comparators = []
            for word in words:
                expanded = self.term(word)
                if expanded is None:
                    return None
                comparators += expanded
            found.append(comparators)
        return found

    def expand_range(self, version_range: str) -> list[str]:
        found = self.sets(version_range)
        if found is None:
            return []
        return [" ".join(op + self.write(v) for op, v in s) for s in found]

    def comparator_holds(self, version: tuple, op: str, bound: tuple) -> bool:
        sign = self.compare_parsed(version, bound)
        return {"=": sign == 0, "<": sign < 0, "<=": sign <= 0, ">": sign > 0, ">=": sign >= 0}[op]

    def pre_allowed(self, version: tuple, comparators: list[tuple[str, tuple]]) -> bool:
        if not version[3]:
            return True
        return any(bound[3] and bound[:3] == version[:3] for _, bound in comparators)

    def set_holds(self, version: tuple, comparators: list[tuple[str, tuple]]) -> bool:
        return all(
            self.comparator_holds(version, op, bound) for op, bound in comparators
        ) and self.pre_allowed(version, comparators)

    def matches(self, version: tuple, found: list[list[tuple[str, tuple]]]) -> bool:
        return any(self.set_holds(version, s) for s in found)

    def satisfies(self, version: str, version_range: str) -> bool:
        parsed, found = self.parse(version), self.sets(version_range)
        return parsed is not None and found is not None and self.matches(parsed[:4], found)

    def max_satisfying(self, versions: list[str], version_range: str) -> str:
        found = [v for v in self.sort_versions(versions) if self.satisfies(v, version_range)]
        return found[-1] if found else ""

    # --- registry
    def publish(self, name: str, version: str, dependencies: list[list[str]]) -> str:
        parsed = self.parse(version)
        if parsed is None:
            return "invalid-version"
        if self.is_duplicate(name, version):
            return "duplicate"
        names = [d[0] for d in dependencies]
        if (
            len(set(names)) < len(names)
            or name in names
            or any(self.sets(r) is None for _, r in dependencies)
        ):
            return "invalid-dependency"
        deps = [(d, r) for d, r in dependencies]
        self.registry.setdefault(name, []).append((version, parsed[:4], deps))
        self.history.append((name, version, deps))
        return "ok"

    def is_duplicate(self, name: str, version: str) -> bool:
        return any(self.compare(version, v) == 0 for v, _, _ in self.registry.get(name, []))

    def newest_first(self, name: str) -> list[tuple[str, tuple, list[tuple[str, str]]]]:
        return sorted(
            self.registry.get(name, []),
            key=cmp_to_key(lambda x, y: self.compare(y[0], x[0])),
        )

    def candidates(self, name: str, version_range: str) -> list[str]:
        return [v for v, _, _ in self.newest_first(name) if self.satisfies(v, version_range)]

    def next_package(self, open_names: set[str], order: list[str]) -> str:
        return min(open_names)

    def search(
        self,
        roots: list[tuple[str, str]],
        kept: set[tuple] | None = None,
        lock: dict[str, str] | None = None,
    ) -> dict[str, str] | None:
        """Chosen versions by name, or None. `kept` limits the constraints in force."""

        def live(constraint: tuple) -> bool:
            return kept is None or constraint in kept

        root_ranges = [(n, r) for i, (n, r) in enumerate(roots) if live(("root", i))]
        lock = lock or {}

        def deps_of(name: str, version: str) -> list[tuple[str, str]]:
            for n, v, deps in self.history:
                if n == name and v == version:
                    return [(d, r) for d, r in deps if live(("dep", n, v, d))]
            return []

        def step(chosen: dict[str, str], order: list[str]) -> dict[str, str] | None:
            wanted = list(root_ranges)
            for name, version in chosen.items():
                wanted += deps_of(name, version)
            open_names = {n for n, _ in wanted} - chosen.keys()
            if not open_names:
                return chosen
            name = self.next_package(open_names, order + [n for n, _ in wanted])
            ranges = [r for n, r in wanted if n == name]
            options = [v for v, _, _ in self.newest_first(name)]
            if name in lock and lock[name] in options:
                options.remove(lock[name])
                options.insert(0, lock[name])
            for version in options:
                if not all(self.satisfies(version, r) for r in ranges):
                    continue
                if not self.fits_chosen(chosen, deps_of(name, version)):
                    continue
                result = step({**chosen, name: version}, [*order, name])
                if result is not None:
                    return result
            return None

        return step({}, [])

    def fits_chosen(self, chosen: dict[str, str], deps: list[tuple[str, str]]) -> bool:
        return all(self.satisfies(chosen[d], r) for d, r in deps if d in chosen)

    def listing(self, chosen: dict[str, str] | None) -> list[str]:
        return [] if chosen is None else [f"{n}@{v}" for n, v in sorted(chosen.items())]

    def resolve(self, requirements: list[list[str]]) -> list[str]:
        return self.listing(self.search([(n, r) for n, r in requirements]))

    # --- explanations and locks
    def constraints(self, roots: list[tuple[str, str]]) -> list[tuple[tuple, str]]:
        found: list[tuple[tuple, str]] = [
            (("root", i), f"root requires {n} {r}") for i, (n, r) in enumerate(roots)
        ]
        for name, version, deps in self.history:
            found += [
                (("dep", name, version, d), f"{name}@{version} requires {d} {r}") for d, r in deps
            ]
        return found

    def explain(self, requirements: list[list[str]]) -> list[str]:
        roots = [(n, r) for n, r in requirements]
        if self.search(roots) is not None:
            return []
        every = self.constraints(roots)
        kept = {key for key, _ in every}
        for key, _ in every:
            if self.search(roots, kept - {key}) is None:
                kept.discard(key)
        return [line for key, line in every if key in kept]

    def lock_of(self, lock: list[str]) -> dict[str, str]:
        return {entry.split("@")[0]: entry.split("@")[1] for entry in lock}

    def locked_resolve(self, requirements: list[list[str]], lock: list[str]) -> list[str]:
        roots = [(n, r) for n, r in requirements]
        return self.listing(self.search(roots, lock=self.lock_of(lock)))

    def update(
        self, requirements: list[list[str]], lock: list[str], unlock: list[str]
    ) -> list[str]:
        old = self.lock_of(lock)
        keep = {n: v for n, v in old.items() if n not in unlock}
        new = self.search([(n, r) for n, r in requirements], lock=keep)
        if new is None:
            return ["unsatisfiable"]
        lines = []
        for name in sorted(set(old) | set(new)):
            if name not in old:
                lines.append(f"{name}: added {new[name]}")
            elif name not in new:
                lines.append(f"{name}: removed {old[name]}")
            elif old[name] != new[name]:
                lines.append(
                    f"{name}: {old[name]} -> {new[name]} ({self.change_kind(old[name], new[name])})"
                )
        return lines


# ------------------------------------------------------------------ level 1 mistakes
class CoreComparedAsText(Model):
    """Compares major, minor and patch as strings, so 1.10.0 sorts before 1.9.0."""

    def compare_parsed(self, a: tuple, b: tuple) -> int:
        x, y = [str(n) for n in a[:3]], [str(n) for n in b[:3]]
        if x != y:
            return (x > y) - (x < y)
        return self.compare_pre(a[3], b[3])


class PreReleaseIdentifiersAsText(Model):
    """Compares numeric pre-release identifiers as text, so beta.11 sorts before beta.2."""

    def compare_identifiers(self, a: str, b: str) -> int:
        return (a > b) - (a < b)


class NumbersAfterWords(Model):
    """Gives numeric identifiers higher precedence than alphanumeric ones."""

    def compare_identifiers(self, a: str, b: str) -> int:
        if a.isdigit() != b.isdigit():
            return 1 if a.isdigit() else -1
        return super().compare_identifiers(a, b)


class ShorterPreReleaseIsHigher(Model):
    """Reads alpha.1 as lower than alpha."""

    def compare_pre(self, a: tuple, b: tuple) -> int:
        if a and b and a != b and (a[: len(b)] == b or b[: len(a)] == a):
            return (len(a) < len(b)) - (len(a) > len(b))
        return super().compare_pre(a, b)


class PreReleaseAboveRelease(Model):
    """Puts a pre-release after its normal version."""

    def compare_pre(self, a: tuple, b: tuple) -> int:
        if not a or not b:
            return (len(a) > 0) - (len(b) > 0)
        return super().compare_pre(a, b)


class BuildMetadataCounts(Model):
    """Breaks precedence ties with the build metadata."""

    def compare_parsed(self, a: tuple, b: tuple) -> int:
        sign = super().compare_parsed(a, b)
        if sign == 0 and len(a) > 4 and len(b) > 4:
            x, y = a[4] or "", b[4] or ""
            return (x > y) - (x < y)
        return sign


class LeadingZerosAllowed(Model):
    """Accepts 01 as a number."""

    def number_ok(self, text: str) -> bool:
        return text.isdigit()


class LeadingZeroInWordsRefused(Model):
    """Refuses 01a, an alphanumeric identifier, as if it were a number with a leading zero."""

    def pre_ok(self, text: str) -> bool:
        return super().pre_ok(text) and not (len(text) > 1 and text[0] == "0")


class BuildNumbersNeedNoLeadingZero(Model):
    """Applies the leading-zero rule to build metadata too."""

    def build_ok(self, text: str) -> bool:
        return super().build_ok(text) and not (text.isdigit() and not self.number_ok(text))


class EmptyIdentifiersAllowed(Model):
    """Accepts 1.0.0-alpha..1 and a trailing dot."""

    def pre_ok(self, text: str) -> bool:
        return text == "" or super().pre_ok(text)


class CaseInsensitivePreRelease(Model):
    """Compares RC and rc as the same letters."""

    def compare_identifiers(self, a: str, b: str) -> int:
        return super().compare_identifiers(a.lower(), b.lower())


class LeadingVAccepted(Model):
    """Accepts v1.0.0, as some tools do."""

    def parse(self, text: str) -> tuple | None:
        return super().parse(text[1:] if text.startswith("v") else text)


class SortDropsRepeats(Model):
    """Lists a repeated version once."""

    def sort_versions(self, versions: list[str]) -> list[str]:
        return super().sort_versions(list(dict.fromkeys(versions)))


class SortKeepsInputOrderOnTies(Model):
    """Leaves versions of equal precedence in the order given."""

    def sort_versions(self, versions: list[str]) -> list[str]:
        valid = [v for v in versions if self.parse(v) is not None]
        return sorted(valid, key=cmp_to_key(self.compare))


class BuildChangeIsAPatch(Model):
    """Calls a change of build metadata a patch."""

    def change_kind(self, before: str, after: str) -> str:
        kind = super().change_kind(before, after)
        return "patch" if kind == "none" and before != after else kind


class FinalReleaseIsAPatch(Model):
    """Calls the step from a pre-release to its release a patch."""

    def change_kind(self, before: str, after: str) -> str:
        kind = super().change_kind(before, after)
        return "patch" if kind == "pre-release" else kind


class DowngradeByFirstDifference(Model):
    """Names the part that changed even when the new version is lower."""

    def change_kind(self, before: str, after: str) -> str:
        kind = super().change_kind(before, after)
        if kind != "downgrade":
            return kind
        a, b = self.parse(before), self.parse(after)
        assert a is not None
        assert b is not None
        for index, word in enumerate(("major", "minor", "patch")):
            if a[index] != b[index]:
                return word
        return "pre-release"


# ------------------------------------------------------------------ level 2 mistakes
class CaretIgnoresZeroMajor(Model):
    """Treats ^0.2.3 like ^1.2.3: everything below the next major."""

    def caret_top(self, numbers: list[int], full: bool) -> tuple:
        return (([*numbers, 0])[0] + 1, 0, 0, LOWEST)


class CaretStopsAtMinor(Model):
    """Never narrows ^0.0.3 to the patch: allows 0.0.x."""

    def caret_top(self, numbers: list[int], full: bool) -> tuple:
        top = super().caret_top(numbers, full)
        return (0, numbers[1] + 1, 0, LOWEST) if top[:2] == (0, 0) else top


class PartialCaretOnZeroZero(Model):
    """Reads ^0.0 as ^0.0.0, allowing only 0.0.0."""

    def caret_top(self, numbers: list[int], full: bool) -> tuple:
        return super().caret_top(numbers, True)


class TildeOnMajorOnlyAllowsPatches(Model):
    """Reads ~1 as ~1.0.0."""

    def tilde_top(self, numbers: list[int]) -> tuple:
        return (numbers[0], ([*numbers, 0])[1] + 1, 0, LOWEST)


class UpperBoundWithoutPreReleaseMark(Model):
    """Writes the exclusive upper bound as <2.0.0 instead of <2.0.0-0."""

    def write(self, version: tuple) -> str:
        if version[3] == LOWEST:
            return f"{version[0]}.{version[1]}.{version[2]}"
        return super().write(version)


class PreReleasesAlwaysIn(Model):
    """Lets every pre-release into every range that its precedence fits."""

    def pre_allowed(self, version: tuple, comparators: list[tuple[str, tuple]]) -> bool:
        return True


class PreReleasesNeverIn(Model):
    """Shuts every pre-release out, even where the range names it."""

    def pre_allowed(self, version: tuple, comparators: list[tuple[str, tuple]]) -> bool:
        return not version[3]


class AnyPreReleaseComparatorOpensTheSet(Model):
    """Lets a pre-release in when any comparator has one, whatever its version."""

    def pre_allowed(self, version: tuple, comparators: list[tuple[str, tuple]]) -> bool:
        return not version[3] or any(bound[3] for _, bound in comparators)


class UnionAsIntersection(Model):
    """Requires every set of the range instead of one."""

    def matches(self, version: tuple, found: list[list[tuple[str, tuple]]]) -> bool:
        return all(self.set_holds(version, s) for s in found)


class OneSpaceOnly(Model):
    """Splits terms on single spaces and refuses the empty terms that runs of spaces leave."""

    def sets(self, text: str) -> list[list[tuple[str, tuple]]] | None:
        if any("  " in piece.strip() for piece in self.pieces(text)):
            return None
        return super().sets(text)


class EqualsTakesFullVersionsOnly(Model):
    """Refuses =1.2."""

    def partial_allowed(self, op: str) -> bool:
        return op in ("", "^", "~")


class ComparatorsTakePartials(Model):
    """Accepts >1.x and <1 as if the pattern were padded with zeros."""

    def partial_allowed(self, op: str) -> bool:
        return True

    def term(self, text: str) -> list[tuple[str, tuple]] | None:
        op = re.match(r"(>=|<=|>|<)?", text).group(0)  # type: ignore[union-attr]
        if op:
            numbers = self.wildcard_numbers(text[len(op) :])
            if numbers is not None and self.parse(text[len(op) :]) is None:
                return [(op, (*([*numbers, 0, 0, 0])[:3], ()))]
        return super().term(text)


class WildcardInTheMiddle(Model):
    """Accepts 1.x.3 as 1.x."""

    def wildcard_numbers(self, pattern: str) -> list[int] | None:
        parts = pattern.split(".")
        numbers: list[int] = []
        for part in parts:
            if part in ("x", "X", "*"):
                return numbers if 1 <= len(parts) <= 3 else None
            if not self.number_ok(part):
                return None
            numbers.append(int(part))
        return numbers if len(numbers) < 3 else None


class MaxSatisfyingPicksTheFirstOfATie(Model):
    """Keeps the first of two versions of equal precedence."""

    def max_satisfying(self, versions: list[str], version_range: str) -> str:
        best = ""
        for v in versions:
            if self.satisfies(v, version_range) and (not best or self.compare(v, best) > 0):
                best = v
        return best


# ------------------------------------------------------------------ level 3 mistakes
class DiscoveryOrder(Model):
    """Decides packages in the order they were first required, not by name."""

    def next_package(self, open_names: set[str], order: list[str]) -> str:
        return next(n for n in order if n in open_names)


class NoBacktracking(Model):
    """Takes the first acceptable version of each package and never goes back."""

    def search(self, roots, kept=None, lock=None):  # type: ignore[no-untyped-def]
        chosen: dict[str, str] = {}
        while True:
            wanted = list(roots)
            for name, version in chosen.items():
                wanted += next(deps for n, v, deps in self.history if n == name and v == version)
            open_names = {n for n, _ in wanted} - chosen.keys()
            if not open_names:
                return chosen
            name = min(open_names)
            ranges = [r for n, r in wanted if n == name]
            options = [
                v
                for v, _, _ in self.newest_first(name)
                if all(self.satisfies(v, r) for r in ranges)
            ]
            if not options:
                return None
            chosen[name] = options[0]


class NoCheckAgainstChosen(Model):
    """Accepts a version without checking its dependencies on the packages already chosen."""

    def fits_chosen(self, chosen: dict[str, str], deps: list[tuple[str, str]]) -> bool:
        return True


class OldestFirst(Model):
    """Tries the versions from the lowest up."""

    def newest_first(self, name: str) -> list[tuple[str, tuple, list[tuple[str, str]]]]:
        return list(reversed(super().newest_first(name)))


class DuplicateByText(Model):
    """Treats 1.0.0+b as a new version next to 1.0.0+a."""

    def is_duplicate(self, name: str, version: str) -> bool:
        return any(version == v for v, _, _ in self.registry.get(name, []))


class SelfDependencyAllowed(Model):
    """Publishes a version that depends on its own package."""

    def publish(self, name: str, version: str, dependencies: list[list[str]]) -> str:
        parsed = self.parse(version)
        own = any(d == name for d, _ in dependencies)
        if own and parsed is not None and not self.is_duplicate(name, version):
            deps = [(d, r) for d, r in dependencies]
            self.registry.setdefault(name, []).append((version, parsed[:4], deps))
            self.history.append((name, version, deps))
            return "ok"
        return super().publish(name, version, dependencies)


class FirstRootRangeOnly(Model):
    """Applies only the first root requirement on a package."""

    def resolve(self, requirements: list[list[str]]) -> list[str]:
        first: dict[str, str] = {}
        for n, r in requirements:
            first.setdefault(n, r)
        return self.listing(self.search(list(first.items())))


class CandidatesOldestFirst(Model):
    """Lists the candidates from the lowest up."""

    def candidates(self, name: str, version_range: str) -> list[str]:
        return list(reversed(super().candidates(name, version_range)))


# ------------------------------------------------------------------ level 4 mistakes
class ExplainEverything(Model):
    """Lists every constraint instead of a minimal set."""

    def explain(self, requirements: list[list[str]]) -> list[str]:
        roots = [(n, r) for n, r in requirements]
        if self.search(roots) is not None:
            return []
        return [line for _, line in self.constraints(roots)]


class ExplainBackwards(Model):
    """Tries the constraints for removal from the last one back."""

    def explain(self, requirements: list[list[str]]) -> list[str]:
        roots = [(n, r) for n, r in requirements]
        if self.search(roots) is not None:
            return []
        every = self.constraints(roots)
        kept = {key for key, _ in every}
        for key, _ in reversed(every):
            if self.search(roots, kept - {key}) is None:
                kept.discard(key)
        return [line for key, line in every if key in kept]


class ExplainRootsOnly(Model):
    """Blames only the root requirements."""

    def explain(self, requirements: list[list[str]]) -> list[str]:
        return [line for line in super().explain(requirements) if line.startswith("root ")]


class ExplainWithoutRetrying(Model):
    """Drops a constraint only if the search fails without it, but never puts it back."""

    def explain(self, requirements: list[list[str]]) -> list[str]:
        roots = [(n, r) for n, r in requirements]
        if self.search(roots) is not None:
            return []
        every = self.constraints(roots)
        return [
            line
            for key, line in every
            if self.search(roots, {k for k, _ in every} - {key}) is not None
        ]


class LockIgnored(Model):
    """Resolves from scratch whatever the lock says."""

    def locked_resolve(self, requirements: list[list[str]], lock: list[str]) -> list[str]:
        return self.resolve(requirements)


class LockForced(Model):
    """Keeps a locked version even when it no longer satisfies, and fails instead of moving."""

    def locked_resolve(self, requirements: list[list[str]], lock: list[str]) -> list[str]:
        chosen = self.search([(n, r) for n, r in requirements], lock=self.lock_of(lock))
        if chosen is None:
            return []
        old = self.lock_of(lock)
        if any(
            n in old and old[n] != v and old[n] in [x for x, _, _ in self.registry.get(n, [])]
            for n, v in chosen.items()
        ):
            return []
        return self.listing(chosen)


class LockOnlyForRoots(Model):
    """Prefers locked versions of the root packages only."""

    def locked_resolve(self, requirements: list[list[str]], lock: list[str]) -> list[str]:
        roots = {n for n, _ in requirements}
        keep = {n: v for n, v in self.lock_of(lock).items() if n in roots}
        return self.listing(self.search([(n, r) for n, r in requirements], lock=keep))


class UpdateUnlocksEverything(Model):
    """Ignores the list of packages to unlock and updates them all."""

    def update(
        self, requirements: list[list[str]], lock: list[str], unlock: list[str]
    ) -> list[str]:
        return super().update(requirements, lock, [n for n, _ in self.lock_of(lock).items()])


class UpdateForgetsRemovals(Model):
    """Reports only the packages of the new resolution."""

    def update(
        self, requirements: list[list[str]], lock: list[str], unlock: list[str]
    ) -> list[str]:
        return [
            line for line in super().update(requirements, lock, unlock) if ": removed " not in line
        ]


class UpdateEmptyWhenUnsatisfiable(Model):
    """Says nothing changes when nothing can be resolved."""

    def update(
        self, requirements: list[list[str]], lock: list[str], unlock: list[str]
    ) -> list[str]:
        lines = super().update(requirements, lock, unlock)
        return [] if lines == ["unsatisfiable"] else lines


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type()
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (
        IndexError,
        KeyError,
        ValueError,
        TypeError,
        AttributeError,
        StopIteration,
        AssertionError,
    ):
        return False


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_two_visible_and_two_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in CASES if case["level"] == level]
        assert sum(bool(case.get("visible")) for case in at_level) >= 2
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_the_hidden_cases_give_every_change_kind_and_status():
    seen = set()
    for case in HIDDEN_CASES:
        for op, got in zip(case["ops"], case["expected"], strict=True):
            if op in ("changeKind", "publish"):
                seen.add(got)
    assert seen >= {
        "major",
        "minor",
        "patch",
        "pre-release",
        "none",
        "downgrade",
        "invalid",
        "ok",
        "duplicate",
        "invalid-version",
        "invalid-dependency",
    }
