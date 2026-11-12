"""agent-trace-analyzer promises that its hidden cases catch the classic mistakes of reading an
agent's trace: duplicates, orphans and loops handled the wrong way or reported out of order, a tree
walked in arrival order, overlapping children counted twice or not clipped, a critical path that
follows one child per level or takes the wrong tie, costs rounded per span or the wrong way, prices
read from the wrong attribute, retry loops found across parents or through successes, arguments
compared before they are normalized, and a root cause taken from the top of the trace instead of
the first failure. These tests replay every case against a model of the analyzer written from the
statement, which must give every expected output, and against that model with one mistake planted
at a time, which some hidden case must fail. A mistake that crashes fails its case, as a thrown
exception does in the grader."""

import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0331-agent-trace-analyzer"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
SCRIPTED_CASES = [case for case in CASES if "ops" in case]
HIDDEN_CASES = [case for case in SCRIPTED_CASES if not case.get("visible", False)]

CODE_ORDER = ["duplicate_id", "end_before_start", "unknown_parent", "parent_cycle"]


@dataclass
class Span:
    position: int
    id: str
    parent: str
    kind: str
    name: str
    start: int
    raw_end: int
    status: str
    attributes: list[str] = field(default_factory=list)


class Model:
    """The analyzer as the statement words it. The events are kept as given, and every answer is
    worked out again from them, bottom-up: a span finds its root by walking up its parents, a self
    time is a sweep over the children's endpoints, and money is kept as exact fractions."""

    def __init__(self) -> None:
        self.events: list[Span] = []
        self.prices: dict[str, tuple[int, int]] = {}

    # --- level 1
    def add_span(
        self,
        span_id: str,
        parent_id: str,
        kind: str,
        name: str,
        start: int,
        end: int,
        status: str,
        attributes: list[str],
    ) -> bool:
        fresh = all(event.id != span_id for event in self.events)
        position = len(self.events)
        self.events.append(
            Span(position, span_id, parent_id, kind, name, start, end, status, list(attributes))
        )
        return fresh

    def spans(self) -> dict[str, Span]:
        """The span of each id: the first event that used it."""
        found: dict[str, Span] = {}
        for event in self.events:
            found.setdefault(event.id, event)
        return found

    def is_duplicate(self, event: Span) -> bool:
        return self.spans()[event.id] is not event

    def end(self, span: Span) -> int:
        return span.raw_end if span.raw_end >= span.start else span.start

    def parent_of(self, span: Span) -> str | None:
        """The parent in the tree, "" for a root, None for a span whose parents loop."""
        spans = self.spans()
        seen = {span.id}
        current = span
        while current.parent:
            if current.parent not in spans:
                break
            current = spans[current.parent]
            if current.id in seen:
                return None
            seen.add(current.id)
        if span.parent in spans:
            return span.parent
        return self.orphan_parent()

    def orphan_parent(self) -> str | None:
        return ""

    def in_tree(self, span: Span) -> bool:
        return self.parent_of(span) is not None

    def tree(self) -> list[Span]:
        return [span for span in self.spans().values() if self.in_tree(span)]

    def child_order(self, span: Span) -> Any:
        return (span.start, span.id)

    def children(self, parent: str) -> list[Span]:
        found = [span for span in self.tree() if self.parent_of(span) == parent]
        return sorted(found, key=self.child_order)

    def depth_of(self, span: Span) -> int:
        depth = self.first_depth()
        while (parent := self.parent_of(span)) not in ("", None):
            span = self.spans()[parent]
            depth += 1
        return depth

    def first_depth(self) -> int:
        return 1

    def codes(self, event: Span) -> list[str]:
        if self.is_duplicate(event):
            return ["duplicate_id"]
        found = []
        if event.raw_end < event.start:
            found.append("end_before_start")
        if event.parent and event.parent not in self.spans():
            found.append("unknown_parent")
        if not self.in_tree(event):
            found.append("parent_cycle")
        return sorted(found, key=self.code_rank)

    def code_rank(self, code: str) -> int:
        return CODE_ORDER.index(code)

    def error_rows(self) -> list[tuple[int, str, str]]:
        return [
            (event.position, code, event.id) for event in self.events for code in self.codes(event)
        ]

    def errors(self) -> list[list[str]]:
        return [[str(position), code, span_id] for position, code, span_id in self.error_rows()]

    def walk(self, parent: str) -> list[Span]:
        found = []
        for child in self.children(parent):
            found.append(child)
            found += self.walk(child.id)
        return found

    def outline(self) -> list[list[str]]:
        return [[str(self.depth_of(span)), span.id, span.kind, span.name] for span in self.walk("")]

    def depth(self) -> int:
        return max((self.depth_of(span) for span in self.tree()), default=0)

    def counted(self) -> list[Span]:
        return self.tree()

    def kind_counts(self) -> list[list[str]]:
        kinds = sorted({span.kind for span in self.counted()})
        return [[kind, str(sum(s.kind == kind for s in self.counted()))] for kind in kinds]

    # --- level 2
    def tree_span(self, span_id: str) -> Span | None:
        span = self.spans().get(span_id)
        return span if span is not None and self.in_tree(span) else None

    def total(self, span: Span) -> int:
        return self.end(span) - span.start

    def child_intervals(self, span: Span) -> list[tuple[int, int]]:
        return [
            (max(child.start, span.start), min(self.end(child), self.end(span)))
            for child in self.children(span.id)
        ]

    def covered(self, intervals: list[tuple[int, int]]) -> int:
        """A sweep over the endpoints: time counts while at least one interval is open."""
        points = sorted(
            [(low, 1) for low, high in intervals if high > low]
            + [(high, -1) for low, high in intervals if high > low]
        )
        open_count, last, covered = 0, 0, 0
        for at, change in points:
            if open_count > 0:
                covered += at - last
            open_count += change
            last = at
        return covered

    def self_time(self, span: Span) -> int:
        return self.total(span) - self.covered(self.child_intervals(span))

    def timing(self, span_id: str) -> list[int]:
        span = self.tree_span(span_id)
        return [] if span is None else [self.total(span), self.self_time(span)]

    def critical_root(self) -> Span | None:
        roots = self.children("")
        if not roots:
            return None
        return sorted(roots, key=lambda span: (-self.end(span), span.start, span.id))[0]

    def last_key(self, child: Span) -> Any:
        return (-self.end(child), child.start, child.id)

    def blocks(self, child: Span, cursor: int) -> bool:
        return self.end(child) <= cursor

    def first_cursor(self, span: Span) -> int:
        return self.end(span)

    def critical_children(self, span: Span) -> list[Span]:
        cursor = self.first_cursor(span)
        left = self.children(span.id)
        chosen = []
        while candidates := [child for child in left if self.blocks(child, cursor)]:
            last = sorted(candidates, key=self.last_key)[0]
            chosen.append(last)
            left.remove(last)
            cursor = last.start
        return self.in_time_order(chosen)

    def in_time_order(self, chosen: list[Span]) -> list[Span]:
        return chosen[::-1]

    def critical_from(self, span: Span) -> list[Span]:
        path = [span]
        for child in self.critical_children(span):
            path += self.critical_from(child)
        return path

    def critical(self) -> list[Span]:
        root = self.critical_root()
        return [] if root is None else self.critical_from(root)

    def critical_path(self) -> list[str]:
        return [span.id for span in self.critical()]

    def slow_key(self, span: Span) -> Any:
        return (-self.self_time(span), -self.total(span), span.id)

    def slowest(self, n: int) -> list[list[str]]:
        ranked = sorted(self.tree(), key=self.slow_key)[:n]
        return [[s.id, str(self.self_time(s)), str(self.total(s))] for s in ranked]

    # --- level 3
    def set_price(self, model: str, input_price: int, output_price: int) -> bool:
        fresh = model not in self.prices
        self.prices[model] = (input_price, output_price)
        return fresh

    def attribute(self, span: Span, key: str) -> str | None:
        for attribute in span.attributes:
            name, separator, value = attribute.partition("=")
            if separator and name == key:
                return value
        return None

    def tokens(self, span: Span) -> tuple[int, int]:
        return (
            int(self.attribute(span, "input_tokens") or 0),
            int(self.attribute(span, "output_tokens") or 0),
        )

    def unpriced_span(self, span: Span) -> bool:
        return sum(self.tokens(span)) > 0 and self.attribute(span, "model") not in self.prices

    def exact_cost(self, span: Span) -> Fraction:
        """The cost in micros, as an exact fraction."""
        if self.unpriced_span(span):
            return Fraction(0)
        model = self.attribute(span, "model")
        price_in, price_out = self.prices.get(model or "", (0, 0))
        tokens_in, tokens_out = self.tokens(span)
        return Fraction(tokens_in * price_in + tokens_out * price_out, 1000)

    def rounded(self, cost: Fraction) -> int:
        return math.floor(cost + Fraction(1, 2))

    def subtree(self, span: Span) -> list[Span]:
        return [span, *self.walk(span.id)]

    def subtree_cost(self, members: list[Span]) -> int:
        return self.rounded(sum((self.exact_cost(member) for member in members), Fraction(0)))

    def rollup(self, span_id: str) -> list[int]:
        span = self.tree_span(span_id)
        if span is None:
            return []
        members = self.subtree(span)
        return [
            *self.tokens(span),
            self.rounded(self.exact_cost(span)),
            sum(self.tokens(member)[0] for member in members),
            sum(self.tokens(member)[1] for member in members),
            self.subtree_cost(members),
        ]

    def priced(self) -> list[Span]:
        return self.tree()

    def kind_key(self, kind: str, exact: Fraction) -> Any:
        return (-exact, kind)

    def cost_by_kind(self) -> list[list[str]]:
        rows = []
        for kind in {span.kind for span in self.priced()}:
            members = [span for span in self.priced() if span.kind == kind]
            exact = sum((self.exact_cost(member) for member in members), Fraction(0))
            rows.append((self.kind_key(kind, exact), kind, members))
        rows.sort(key=lambda row: row[0])
        return [
            [
                kind,
                str(sum(self.tokens(m)[0] for m in members)),
                str(sum(self.tokens(m)[1] for m in members)),
                str(self.subtree_cost(members)),
            ]
            for _, kind, members in rows
        ]

    def unpriced(self) -> list[str]:
        return sorted(span.id for span in self.priced() if self.unpriced_span(span))

    # --- level 4
    def args_pieces(self, text: str) -> list[str]:
        return [piece for piece in (raw.strip(" ") for raw in text.split("&")) if piece]

    def normalize_pair(self, piece: str) -> tuple[str, str]:
        name, _, value = piece.partition("=")
        return name.strip(" ").lower(), value.strip(" ")

    def normalized(self, text: str) -> str:
        pairs = sorted(self.normalize_pair(piece) for piece in self.args_pieces(text))
        return "&".join(f"{name}={value}" for name, value in pairs)

    def call(self, span: Span) -> tuple[str, str]:
        return span.name, self.normalized(self.attribute(span, "args") or "")

    def sibling_groups(self) -> list[list[Span]]:
        parents = [""] + [span.id for span in self.tree()]
        return [self.children(parent) for parent in parents]

    def in_run(self, span: Span) -> bool:
        return span.kind == "tool"

    def breaks_run(self, span: Span) -> bool:
        return False

    def extends(self, run: list[Span], span: Span) -> bool:
        return span.status == "error" and self.call(span) == self.call(run[0])

    def long_enough(self, run: list[Span], min_run: int) -> bool:
        return len(run) >= min_run

    def runs(self, min_run: int) -> list[list[Span]]:
        found = []
        for group in self.sibling_groups():
            run: list[Span] = []
            for span in group:
                if self.breaks_run(span):
                    run = []
                    continue
                if not self.in_run(span):
                    continue
                if run and self.extends(run, span):
                    run.append(span)
                    continue
                if self.long_enough(run, min_run):
                    found.append(run)
                run = [span] if span.status == "error" else []
            if self.long_enough(run, min_run):
                found.append(run)
        return sorted(found, key=lambda run: (run[0].start, run[0].id))

    def retry_loops(self, min_run: int) -> list[list[str]]:
        return [
            [run[0].id, run[-1].id, run[0].name, self.call(run[0])[1], str(len(run))]
            for run in self.runs(min_run)
        ]

    def failed(self) -> bool:
        path = self.critical()
        return bool(path) and path[0].status == "error"

    def suspects(self) -> list[Span]:
        return [span for span in self.critical() if span.status == "error"]

    def cause_key(self, span: Span) -> Any:
        return (self.end(span), -self.depth_of(span), span.id)

    def cause(self) -> Span | None:
        if not self.failed():
            return None
        return min(self.suspects(), key=self.cause_key)

    def root_cause(self) -> list[str]:
        cause = self.cause()
        return [] if cause is None else [cause.id, cause.kind, cause.name]

    def malformed(self) -> int:
        return len({position for position, _, _ in self.error_rows()})

    def repeated(self, runs: list[list[Span]]) -> int:
        return sum(len(run) - 1 for run in runs)

    def trace_cost(self) -> int:
        return self.subtree_cost(self.tree())

    def report(self, min_run: int) -> list[str]:
        path = self.critical()
        cause = self.cause()
        runs = self.runs(min_run)
        status = "empty" if not path else "failed" if self.failed() else "ok"
        return [
            f"spans: {len(self.tree())}",
            f"depth: {self.depth()}",
            f"malformed: {self.malformed()}",
            f"status: {status}",
            f"critical path: {len(path)}",
            f"duration: {self.total(path[0]) if path else 0}",
            f"root cause: {cause.id if cause else 'none'}",
            f"retry loops: {len(runs)}",
            f"repeated calls: {self.repeated(runs)}",
            f"tokens: {sum(sum(self.tokens(span)) for span in self.tree())}",
            f"cost: {self.trace_cost()}",
            f"unpriced: {len(self.unpriced())}",
        ]


# ------------------------------------------------------------------ level 1 mistakes
class Mistake(Model):
    pass


class DuplicateReplacesTheFirst(Mistake):
    """Lets a later event with the same id replace the first one."""

    def spans(self) -> dict[str, Span]:
        return {event.id: event for event in self.events}


class OrphansDropped(Mistake):
    """Leaves a span whose parent is unknown out of the tree."""

    def orphan_parent(self) -> str | None:
        return None


class CycleSpansKeptAsRoots(Mistake):
    """Puts the spans whose parents loop at the top of the tree."""

    def parent_of(self, span: Span) -> str | None:
        found = super().parent_of(span)
        return "" if found is None else found


class OnlyLoopMembersReported(Mistake):
    """Reports parent_cycle only for the spans on the loop, not for those hanging below it."""

    def codes(self, event: Span) -> list[str]:
        codes = super().codes(event)
        if "parent_cycle" in codes and not self.on_loop(event):
            codes.remove("parent_cycle")
        return codes

    def on_loop(self, span: Span) -> bool:
        spans, current, seen = self.spans(), span, set()
        while current.parent in spans and current.id not in seen:
            seen.add(current.id)
            current = spans[current.parent]
            if current.id == span.id:
                return True
        return False


class ErrorsSortedByCode(Mistake):
    """Sorts the errors by code instead of by position."""

    def error_rows(self) -> list[tuple[int, str, str]]:
        rows = super().error_rows()
        return sorted(rows, key=lambda row: (CODE_ORDER.index(row[1]), row[0]))


class CodesOfAnEventInAnotherOrder(Mistake):
    """Lists unknown_parent and parent_cycle before end_before_start."""

    def code_rank(self, code: str) -> int:
        return {"end_before_start": 9}.get(code, CODE_ORDER.index(code))


class PositionsFromOne(Mistake):
    """Numbers the events from 1."""

    def errors(self) -> list[list[str]]:
        return [[str(position + 1), code, span_id] for position, code, span_id in self.error_rows()]


class ChildrenInArrivalOrder(Mistake):
    """Orders children as their events arrived."""

    def child_order(self, span: Span) -> Any:
        return span.position


class ChildrenByIdOnly(Mistake):
    """Orders children by id alone."""

    def child_order(self, span: Span) -> Any:
        return span.id


class ChildrenByIdIgnoringUnderscores(Mistake):
    """Ties on start are broken by the id with underscores ignored."""

    def child_order(self, span: Span) -> Any:
        return (span.start, span.id.replace("_", ""), span.id)


class DepthCountsFromZero(Mistake):
    """Gives a root the depth 0."""

    def first_depth(self) -> int:
        return 0


class KindCountsIncludeEveryEvent(Mistake):
    """Counts the kinds of every event, duplicates and loops included."""

    def counted(self) -> list[Span]:
        return self.events


# ------------------------------------------------------------------ level 2 mistakes
class OverlapsCountedTwice(Mistake):
    """Subtracts the sum of the children's lengths instead of their union."""

    def covered(self, intervals: list[tuple[int, int]]) -> int:
        return sum(max(0, high - low) for low, high in intervals)


class ChildrenNotClipped(Mistake):
    """Subtracts the children's whole intervals, even outside the span."""

    def child_intervals(self, span: Span) -> list[tuple[int, int]]:
        return [(child.start, self.end(child)) for child in self.children(span.id)]


class EveryDescendantSubtracted(Mistake):
    """Subtracts the union of all descendants, not of the children."""

    def child_intervals(self, span: Span) -> list[tuple[int, int]]:
        return [
            (max(child.start, span.start), min(self.end(child), self.end(span)))
            for child in self.walk(span.id)
        ]


class RawEndForALateSpan(Mistake):
    """Uses the end as given even when it is before the start."""

    def end(self, span: Span) -> int:
        return span.raw_end


class OneCriticalChildPerSpan(Mistake):
    """Follows only the child that ends last, never the siblings before it."""

    def critical_children(self, span: Span) -> list[Span]:
        return super().critical_children(span)[-1:]


class ChildrenPastTheEndCanBeCritical(Mistake):
    """Starts the walk back from the latest child end, even past the span's end."""

    def first_cursor(self, span: Span) -> int:
        return max([self.end(span)] + [self.end(child) for child in self.children(span.id)])


class TouchingChildIsNotCritical(Mistake):
    """Needs a child to end strictly before the cursor."""

    def blocks(self, child: Span, cursor: int) -> bool:
        return self.end(child) < cursor


class LastChildTieGoesToTheLaterStart(Mistake):
    """Breaks a tie on the end by the later start."""

    def last_key(self, child: Span) -> Any:
        return (-self.end(child), -child.start, child.id)


class CriticalChildrenLatestFirst(Mistake):
    """Lists the critical children in the order they were found, latest first."""

    def in_time_order(self, chosen: list[Span]) -> list[Span]:
        return chosen


class CriticalRootIsTheLongest(Mistake):
    """Starts the critical path at the longest root."""

    def critical_root(self) -> Span | None:
        roots = self.children("")
        if not roots:
            return None
        return sorted(roots, key=lambda span: (-self.total(span), span.id))[0]


class SlowestByTotal(Mistake):
    """Ranks the slowest spans by total time."""

    def slow_key(self, span: Span) -> Any:
        return (-self.total(span), -self.self_time(span), span.id)


class SlowestTiesGoToTheShorter(Mistake):
    """Breaks a tie on self time by the smaller total."""

    def slow_key(self, span: Span) -> Any:
        return (-self.self_time(span), self.total(span), span.id)


# ------------------------------------------------------------------ level 3 mistakes
class RoundsEachSpanThenAdds(Mistake):
    """Adds the rounded costs of the spans."""

    def subtree_cost(self, members: list[Span]) -> int:
        return sum(self.rounded(self.exact_cost(member)) for member in members)


class RoundsHalvesToEven(Mistake):
    """Rounds halves to the even micro."""

    def rounded(self, cost: Fraction) -> int:
        return round(cost)


class RoundsDown(Mistake):
    """Drops the fraction of a micro."""

    def rounded(self, cost: Fraction) -> int:
        return math.floor(cost)


class LastAttributeWins(Mistake):
    """Reads the last attribute with a key."""

    def attribute(self, span: Span, key: str) -> str | None:
        found = None
        for attribute in span.attributes:
            name, separator, value = attribute.partition("=")
            if separator and name == key:
                found = value
        return found


class ZeroPriceIsUnpriced(Mistake):
    """Counts a span as unpriced when its price is 0."""

    def unpriced_span(self, span: Span) -> bool:
        model = self.attribute(span, "model")
        return sum(self.tokens(span)) > 0 and self.prices.get(model or "", (0, 0)) == (0, 0)


class SpanWithoutAModelIsNotUnpriced(Mistake):
    """Reports only the spans whose named model has no price."""

    def unpriced_span(self, span: Span) -> bool:
        return super().unpriced_span(span) and self.attribute(span, "model") is not None


class FirstPriceStays(Mistake):
    """Keeps the first price of a model."""

    def set_price(self, model: str, input_price: int, output_price: int) -> bool:
        if model in self.prices:
            return False
        return super().set_price(model, input_price, output_price)


class PricesPerToken(Mistake):
    """Reads the prices as per token instead of per 1000 tokens."""

    def exact_cost(self, span: Span) -> Fraction:
        return super().exact_cost(span) * 1000


class InputAndOutputPricesSwapped(Mistake):
    """Charges input tokens at the output price and the other way round."""

    def tokens(self, span: Span) -> tuple[int, int]:
        return super().tokens(span)

    def exact_cost(self, span: Span) -> Fraction:
        if self.unpriced_span(span):
            return Fraction(0)
        price_in, price_out = self.prices.get(self.attribute(span, "model") or "", (0, 0))
        tokens_in, tokens_out = self.tokens(span)
        return Fraction(tokens_in * price_out + tokens_out * price_in, 1000)


class KindsSortedByName(Mistake):
    """Lists the kinds by name."""

    def kind_key(self, kind: str, exact: Fraction) -> Any:
        return kind


class KindsSortedByRoundedCost(Mistake):
    """Lists the kinds by rounded cost, so near costs fall back to the name."""

    def kind_key(self, kind: str, exact: Fraction) -> Any:
        return (-self.rounded(exact), kind)


class CostsIncludeLoopedSpans(Mistake):
    """Prices the spans whose parents loop as well."""

    def priced(self) -> list[Span]:
        return list(self.spans().values())


# ------------------------------------------------------------------ level 4 mistakes
class ArgumentsComparedAsWritten(Mistake):
    """Compares the arguments without normalizing them."""

    def normalized(self, text: str) -> str:
        return text


class ArgumentNamesKeepTheirCase(Mistake):
    """Leaves the names of the arguments in their case."""

    def normalize_pair(self, piece: str) -> tuple[str, str]:
        name, _, value = piece.partition("=")
        return name.strip(" "), value.strip(" ")


class ArgumentValuesLowercased(Mistake):
    """Lowercases the values as well as the names."""

    def normalize_pair(self, piece: str) -> tuple[str, str]:
        name, value = super().normalize_pair(piece)
        return name, value.lower()


class ArgumentSpacesCollapsed(Mistake):
    """Collapses runs of spaces inside the values."""

    def normalize_pair(self, piece: str) -> tuple[str, str]:
        name, value = super().normalize_pair(piece)
        return name, " ".join(value.split())


class ArgumentPairsNotSorted(Mistake):
    """Keeps the arguments in the order they were written."""

    def normalized(self, text: str) -> str:
        pairs = [self.normalize_pair(piece) for piece in self.args_pieces(text)]
        return "&".join(f"{name}={value}" for name, value in pairs)


class EmptyArgumentPiecesKept(Mistake):
    """Keeps the empty pieces between two & signs."""

    def args_pieces(self, text: str) -> list[str]:
        return [raw.strip(" ") for raw in text.split("&")]


class SuccessDoesNotEndARun(Mistake):
    """Counts a successful call with the same arguments into the run."""

    def extends(self, run: list[Span], span: Span) -> bool:
        return self.call(span) == self.call(run[0])


class RunsAcrossTheWholeTrace(Mistake):
    """Looks for runs among all the tool spans of the trace, whatever their parent."""

    def sibling_groups(self) -> list[list[Span]]:
        return [sorted(self.tree(), key=lambda span: (span.start, span.id))]


class OtherKindsBreakARun(Mistake):
    """Lets a model or retrieval span between two tool calls end the run."""

    def breaks_run(self, span: Span) -> bool:
        return span.kind != "tool"


class RunNeedsMoreThanTheMinimum(Mistake):
    """Reports a run only when it is longer than min_run."""

    def long_enough(self, run: list[Span], min_run: int) -> bool:
        return len(run) > min_run


class LastRunForgotten(Mistake):
    """Never reports a run that reaches the last tool span of its group."""

    def runs(self, min_run: int) -> list[list[Span]]:
        found = super().runs(min_run)
        lasts = {
            [span for span in group if span.kind == "tool"][-1].id
            for group in self.sibling_groups()
            if any(span.kind == "tool" for span in group)
        }
        return [run for run in found if run[-1].id not in lasts]


class CauseIsTheFirstFailureOnThePath(Mistake):
    """Takes the first failing span in the order of the path, the top of the trace."""

    def cause(self) -> Span | None:
        return self.suspects()[0] if self.failed() else None


class CauseTieGoesToTheShallower(Mistake):
    """Breaks a tie on the end by the shallower span."""

    def cause_key(self, span: Span) -> Any:
        return (self.end(span), self.depth_of(span), span.id)


class CauseFromAnywhereInTheTrace(Mistake):
    """Looks for the first failure in the whole trace, not on the critical path."""

    def suspects(self) -> list[Span]:
        return [span for span in self.tree() if span.status == "error"]


class CauseEvenWhenTheTraceSucceeded(Mistake):
    """Names a cause whenever a span on the critical path failed."""

    def failed(self) -> bool:
        return bool(self.suspects())


class MalformedCountsErrors(Mistake):
    """Counts the error rows instead of the events with an error."""

    def malformed(self) -> int:
        return len(self.error_rows())


class RepeatedCountsEveryFailure(Mistake):
    """Counts every failed call of a loop as repeated."""

    def repeated(self, runs: list[list[Span]]) -> int:
        return sum(len(run) for run in runs)


class TraceCostAddsTheRoots(Mistake):
    """Adds the rounded costs of the roots' subtrees."""

    def trace_cost(self) -> int:
        return sum(self.subtree_cost(self.subtree(root)) for root in self.children(""))


MISTAKES: Sequence[type[Model]] = Mistake.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", op).lower()


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type()
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError, ZeroDivisionError, StopIteration):
        return False


@pytest.mark.parametrize("case", SCRIPTED_CASES, ids=[case["id"] for case in SCRIPTED_CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_two_visible_and_two_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in SCRIPTED_CASES if case["level"] == level]
        assert sum(bool(case.get("visible")) for case in at_level) >= 2
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_a_hidden_case_holds_each_error_code_and_a_late_orphan():
    codes = {
        row[1]
        for case in HIDDEN_CASES
        for op, rows in zip(case["ops"], case["expected"], strict=True)
        if op == "errors"
        for row in rows
    }
    assert codes == set(CODE_ORDER)
