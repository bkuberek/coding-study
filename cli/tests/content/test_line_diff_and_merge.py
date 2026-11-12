"""line-diff-and-merge promises that its hidden cases catch the classic mistakes of line diffs,
patches and three-way merges: a tie broken the other way or a diff that is not the shortest, hunks
merged or split at the wrong gap and headers off by one, a patch search that forgets earlier hunks,
breaks ties the other way or moves backwards, and a merge that calls an identical change a conflict,
resolves adjacent changes line by line or drops the base from its markers. These tests replay
every case against a model written from the statement, and against that model with one mistake
planted at a time, which some hidden case must fail.

The model is built differently from the reference: the diff walks a table of edit distances and
checks each step against it, hunks are cut from a mask of the lines near a change, a patch tries the
candidate positions in sorted order, and the merge follows the chunk-by-chunk walk of the paper on
diff3 by Khanna, Kunal and Pierce (FSTTCS 2007)."""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0365-line-diff-and-merge"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]
KEEP, REMOVE, ADD = " ", "-", "+"
MARKERS = ("<<<<<<< ours", "||||||| base", "=======", ">>>>>>> theirs")

Step = tuple[str, str]


class Model:
    def __init__(self) -> None:
        self.last: list[str] = []

    # --- level 1
    def distances(self, before: list[str], after: list[str]) -> list[list[int]]:
        """cost[i][j]: the fewest removed plus added lines that turn before[i:] into after[j:]."""
        n, m = len(before), len(after)
        cost = [[0] * (m + 1) for _ in range(n + 1)]
        for i in range(n, -1, -1):
            for j in range(m, -1, -1):
                if i == n or j == m:
                    cost[i][j] = (n - i) + (m - j)
                elif before[i] == after[j]:
                    cost[i][j] = min(cost[i + 1][j + 1], 1 + min(cost[i + 1][j], cost[i][j + 1]))
                else:
                    cost[i][j] = 1 + min(cost[i + 1][j], cost[i][j + 1])
        return cost

    def script(self, before: list[str], after: list[str]) -> list[Step]:
        cost = self.distances(before, after)
        steps: list[Step] = []
        i = j = 0
        while (i, j) != (len(before), len(after)):
            here = cost[i][j]
            same = i < len(before) and j < len(after) and before[i] == after[j]
            if same and cost[i + 1][j + 1] == here:
                steps.append((KEEP, before[i]))
                i, j = i + 1, j + 1
                continue
            if i < len(before) and cost[i + 1][j] + 1 == here:
                steps.append((REMOVE, before[i]))
                i += 1
            else:
                steps.append((ADD, after[j]))
                j += 1
        return steps

    def lcs(self, before: list[str], after: list[str]) -> list[str]:
        return [line for kind, line in self.script(before, after) if kind == KEEP]

    def diff(self, before: list[str], after: list[str]) -> list[str]:
        return [kind + line for kind, line in self.script(before, after)]

    # --- level 2
    def near_change(self, steps: list[Step], context: int) -> list[bool]:
        """Which lines of the script go in some hunk: a change, or a kept line close to one."""
        changes = [k for k, (kind, _) in enumerate(steps) if kind != KEEP]
        shown = [False] * len(steps)
        for k in changes:
            for near in range(max(0, k - context), min(len(steps), k + context + 1)):
                shown[near] = True
        return shown

    def label(self, before_count: int, count: int) -> str:
        if count == 0:
            return f"{before_count},0"
        return f"{before_count + 1}" if count == 1 else f"{before_count + 1},{count}"

    def unified(self, before: list[str], after: list[str], context: int) -> list[str]:
        steps = self.script(before, after)
        shown = self.near_change(steps, context)
        out: list[str] = []
        k = 0
        while k < len(steps):
            if not shown[k]:
                k += 1
                continue
            end = k
            while end < len(steps) and shown[end]:
                end += 1
            hunk, prior = steps[k:end], steps[:k]
            old_before = len([s for s in prior if s[0] != ADD])
            new_before = len([s for s in prior if s[0] != REMOVE])
            old = len([s for s in hunk if s[0] != ADD])
            new = len([s for s in hunk if s[0] != REMOVE])
            out.append(f"@@ -{self.label(old_before, old)} +{self.label(new_before, new)} @@")
            out += [kind + line for kind, line in hunk]
            k = end
        return out

    # --- level 3
    def parse(self, patch: list[str]) -> list[tuple[int, list[str], list[str]]]:
        hunks = []
        for line in patch:
            if line.startswith("@@ "):
                old_range = line.split()[1][1:]
                start, _, count = old_range.partition(",")
                empty = count == "0"
                hunks.append((int(start) if empty else int(start) - 1, [], []))
            else:
                kind, text = line[0], line[1:]
                if kind != ADD:
                    hunks[-1][1].append(text)
                if kind != REMOVE:
                    hunks[-1][2].append(text)
        return hunks

    def candidates(self, expected: int, max_offset: int) -> list[int]:
        offsets = range(-max_offset, max_offset + 1)
        return [expected + k for k in sorted(offsets, key=lambda k: (abs(k), k))]

    def base_of(self, start: int, added: int) -> int:
        """Where the hunk belongs once the earlier hunks' added and removed lines are counted."""
        return start + added

    def carried(self, last_offset: int) -> int:
        return last_offset

    def apply_patch(self, lines: list[str], patch: list[str], max_offset: int) -> list[str]:
        text = list(lines)
        report = []
        added = last_offset = lowest = 0
        for start, old, new in self.parse(patch):
            base = self.base_of(start, added)
            spots = [
                p
                for p in self.candidates(base + self.carried(last_offset), max_offset)
                if self.allowed(p, lowest)
                and p + len(old) <= len(text)
                and text[p : p + len(old)] == old
            ]
            if not spots:
                report.append("rejected")
                continue
            spot = spots[0]
            text = text[:spot] + new + text[spot + len(old) :]
            last_offset = spot - base
            added += len(new) - len(old)
            lowest = spot + len(new)
            report.append(f"applied {self.reported(last_offset)}")
        self.last = text
        return report

    def allowed(self, position: int, lowest: int) -> bool:
        return position >= lowest

    def reported(self, offset: int) -> int:
        return offset

    def patched(self) -> list[str]:
        return list(self.last)

    # --- level 4
    def matching(self, base: list[str], other: list[str]) -> dict[int, int]:
        pairs = {}
        o = a = 0
        for kind, _ in self.script(base, other):
            if kind == KEEP:
                pairs[o] = a
            o += kind != ADD
            a += kind != REMOVE
        return pairs

    def chunk(self, ours: list[str], base: list[str], theirs: list[str]) -> list[str]:
        if base == theirs:
            return ours
        if base == ours:
            return theirs
        if ours == theirs:
            return ours
        return self.conflict(ours, base, theirs)

    def conflict(self, ours: list[str], base: list[str], theirs: list[str]) -> list[str]:
        start, middle, separator, end = MARKERS
        return [start, *ours, middle, *base, separator, *theirs, end]

    def merge(self, base: list[str], ours: list[str], theirs: list[str]) -> list[str]:
        """Figure 2 of the diff3 paper: stable chunks are runs matched in all three, unstable
        chunks are what lies between them."""
        ma, mb = self.matching(base, ours), self.matching(base, theirs)
        lo = la = lb = 0
        out: list[str] = []
        while True:
            i = 1
            while ma.get(lo + i - 1) == la + i - 1 and mb.get(lo + i - 1) == lb + i - 1:
                i += 1
            if i > 1:
                out += base[lo : lo + i - 1]
                lo, la, lb = lo + i - 1, la + i - 1, lb + i - 1
                continue
            following = [o for o in range(lo, len(base)) if o in ma and o in mb]
            if not following:
                if lo < len(base) or la < len(ours) or lb < len(theirs):
                    out += self.chunk(ours[la:], base[lo:], theirs[lb:])
                return out
            o = following[0]
            out += self.chunk(ours[la : ma[o]], base[lo:o], theirs[lb : mb[o]])
            lo, la, lb = o, ma[o], mb[o]


# ------------------------------------------------------------------ level 1 mistakes
class AddsBeforeRemoves(Model):
    """Breaks a tie by adding first."""

    def script(self, before: list[str], after: list[str]) -> list[Step]:
        return [(kind, line) for kind, line in self.swap(super().script(after, before))]

    def swap(self, steps: list[Step]) -> list[Step]:
        flipped = {KEEP: KEEP, REMOVE: ADD, ADD: REMOVE}
        return [(flipped[kind], line) for kind, line in steps]


class BacktracksFromTheEnd(Model):
    """Fills the table over prefixes and walks back from the end, removing on a tie."""

    def script(self, before: list[str], after: list[str]) -> list[Step]:
        n, m = len(before), len(after)
        best = [[0] * (m + 1) for _ in range(n + 1)]
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                if before[i - 1] == after[j - 1]:
                    best[i][j] = best[i - 1][j - 1] + 1
                else:
                    best[i][j] = max(best[i - 1][j], best[i][j - 1])
        steps: list[Step] = []
        i, j = n, m
        while i or j:
            if i and j and before[i - 1] == after[j - 1]:
                steps.append((KEEP, before[i - 1]))
                i, j = i - 1, j - 1
            elif i and (not j or best[i - 1][j] >= best[i][j - 1]):
                steps.append((REMOVE, before[i - 1]))
                i -= 1
            else:
                steps.append((ADD, after[j - 1]))
                j -= 1
        return steps[::-1]


class MatchesTheNextEqualLine(Model):
    """Keeps a line when it appears later in the other list, without checking it is best."""

    def script(self, before: list[str], after: list[str]) -> list[Step]:
        steps: list[Step] = []
        i = j = 0
        while i < len(before) and j < len(after):
            if before[i] == after[j]:
                steps.append((KEEP, before[i]))
                i, j = i + 1, j + 1
            elif before[i] in after[j:]:
                steps.append((ADD, after[j]))
                j += 1
            else:
                steps.append((REMOVE, before[i]))
                i += 1
        steps += [(REMOVE, line) for line in before[i:]] + [(ADD, line) for line in after[j:]]
        return steps


class AddsWithinARunFirst(Model):
    """Writes the added lines of a change before its removed lines."""

    def script(self, before: list[str], after: list[str]) -> list[Step]:
        steps, run = [], []
        for step in [*super().script(before, after), (KEEP, "")]:
            if step[0] == KEEP:
                steps += [s for s in run if s[0] == ADD] + [s for s in run if s[0] == REMOVE]
                steps.append(step)
                run = []
            else:
                run.append(step)
        return steps[:-1]


# ------------------------------------------------------------------ level 2 mistakes
class GapOfTwiceTheContextSplits(Model):
    """Groups changes by the gap between them and splits at a gap of exactly twice the context."""

    def unified(self, before: list[str], after: list[str], context: int) -> list[str]:
        steps = self.script(before, after)
        changes = [k for k, (kind, _) in enumerate(steps) if kind != KEEP]
        groups: list[list[int]] = []
        for k in changes:
            if groups and k - groups[-1][-1] - 1 < 2 * context:
                groups[-1].append(k)
            else:
                groups.append([k])
        out: list[str] = []
        for group in groups:
            start, end = max(0, group[0] - context), min(len(steps), group[-1] + context + 1)
            prior, hunk = steps[:start], steps[start:end]
            old_range = self.label(sum(s[0] != ADD for s in prior), sum(s[0] != ADD for s in hunk))
            new_range = self.label(
                sum(s[0] != REMOVE for s in prior), sum(s[0] != REMOVE for s in hunk)
            )
            out.append(f"@@ -{old_range} +{new_range} @@")
            out += [kind + line for kind, line in hunk]
        return out


class EmptyRangeStartsAfterTheLineBefore(Model):
    """Numbers an empty range from the line after it."""

    def label(self, before_count: int, count: int) -> str:
        if count == 0:
            return f"{before_count + 1},0"
        return super().label(before_count, count)


class CountAlwaysWritten(Model):
    """Writes `,1` for a range of one line."""

    def label(self, before_count: int, count: int) -> str:
        return f"{before_count + 1},1" if count == 1 else super().label(before_count, count)


class ContextOnlyBeforeAChange(Model):
    """Shows context before a change but not after it."""

    def near_change(self, steps: list[Step], context: int) -> list[bool]:
        shown = super().near_change(steps, context)
        last_change = max((k for k, (kind, _) in enumerate(steps) if kind != KEEP), default=-1)
        return [flag and k <= last_change for k, flag in enumerate(shown)]


class NewRangeUsesTheOldStart(Model):
    """Starts the new range at the old range's line number."""

    def label(self, before_count: int, count: int) -> str:
        self.labels = getattr(self, "labels", 0) + 1
        if self.labels % 2 == 1:
            self.old_start = before_count
        return super().label(self.old_start, count)


# ------------------------------------------------------------------ level 3 mistakes
class SearchIgnoresTheLastOffset(Model):
    """Searches around the hunk's own line number only."""

    def carried(self, last_offset: int) -> int:
        return 0


class SearchIgnoresEarlierHunks(Model):
    """Forgets the lines that earlier hunks added or removed."""

    def base_of(self, start: int, added: int) -> int:
        return start


class LaterCandidateWinsATie(Model):
    """Tries the later of two equally near positions first."""

    def candidates(self, expected: int, max_offset: int) -> list[int]:
        offsets = range(-max_offset, max_offset + 1)
        return [expected + k for k in sorted(offsets, key=lambda k: (abs(k), -k))]


class HunksMayMoveBackwards(Model):
    """Lets a hunk apply before the end of the previous one."""

    def allowed(self, position: int, lowest: int) -> bool:
        return position >= 0


class OffsetFromTheSearchStart(Model):
    """Reports the distance from where the search started."""

    def __init__(self) -> None:
        super().__init__()
        self.previous = 0

    def reported(self, offset: int) -> int:
        shown = offset - self.previous
        self.previous = offset
        return shown


class RejectionStopsThePatch(Model):
    """Rejects every hunk after the first one that fails."""

    def apply_patch(self, lines: list[str], patch: list[str], max_offset: int) -> list[str]:
        report = super().apply_patch(lines, patch, max_offset)
        if "rejected" in report:
            first = report.index("rejected")
            kept = self.hunk_texts(patch)[:first]
            super().apply_patch(lines, [line for hunk in kept for line in hunk], max_offset)
            report = report[:first] + ["rejected"] * (len(report) - first)
        return report

    def hunk_texts(self, patch: list[str]) -> list[list[str]]:
        hunks: list[list[str]] = []
        for line in patch:
            if line.startswith("@@ "):
                hunks.append([])
            hunks[-1].append(line)
        return hunks


# ------------------------------------------------------------------ level 4 mistakes
class SameChangeIsAConflict(Model):
    """Marks a chunk that both sides changed in the same way as a conflict."""

    def chunk(self, ours: list[str], base: list[str], theirs: list[str]) -> list[str]:
        if ours == theirs and ours != base:
            return self.conflict(ours, base, theirs)
        return super().chunk(ours, base, theirs)


class AdjacentChangesMergedLineByLine(Model):
    """Merges a chunk of equal lengths line by line."""

    def chunk(self, ours: list[str], base: list[str], theirs: list[str]) -> list[str]:
        if len(ours) == len(base) == len(theirs) and len(base) > 1:
            return [
                line
                for o, b, t in zip(ours, base, theirs, strict=True)
                for line in super().chunk([o], [b], [t])
            ]
        return super().chunk(ours, base, theirs)


class ConflictWithoutTheBase(Model):
    """Leaves the base section out of a conflict."""

    def conflict(self, ours: list[str], base: list[str], theirs: list[str]) -> list[str]:
        start, _, separator, end = MARKERS
        return [start, *ours, separator, *theirs, end]


class DeletionWinsOverAnEdit(Model):
    """Takes a deletion on one side over an edit on the other."""

    def chunk(self, ours: list[str], base: list[str], theirs: list[str]) -> list[str]:
        if base and (not ours or not theirs):
            return []
        return super().chunk(ours, base, theirs)


class BothInsertionsKept(Model):
    """Keeps both sides' lines, ours first, where both inserted different lines."""

    def chunk(self, ours: list[str], base: list[str], theirs: list[str]) -> list[str]:
        if not base and ours and theirs and ours != theirs:
            return ours + theirs
        return super().chunk(ours, base, theirs)


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
    except (IndexError, KeyError, ValueError, TypeError):
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


def test_every_unified_diff_applies_back_to_the_new_lines():
    """The hunks of level 2 are a patch that level 3 applies without a search."""
    model = Model()
    for case in CASES:
        for op, arguments in zip(case["ops"], case["args"], strict=True):
            if op == "unified":
                before, after, context = arguments
                report = model.apply_patch(before, model.unified(before, after, context), 0)
                assert set(report) <= {"applied 0"}
                assert model.patched() == after
