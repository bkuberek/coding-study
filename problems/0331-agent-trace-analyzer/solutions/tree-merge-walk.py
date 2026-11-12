from collections import defaultdict

DUPLICATE_ID = "duplicate_id"
END_BEFORE_START = "end_before_start"
UNKNOWN_PARENT = "unknown_parent"
PARENT_CYCLE = "parent_cycle"
NANOS_PER_MICRO = 1000


class _Span:
    __slots__ = ("attributes", "end", "id", "kind", "late", "name", "parent", "start", "status")

    def __init__(
        self, fields: tuple[str, str, str, str, int, int, str], attributes: list[str]
    ) -> None:
        self.id, self.parent, self.kind, self.name, self.start, end, self.status = fields
        self.late = end < self.start
        self.end = max(self.start, end)
        self.attributes: dict[str, str] = {}
        for attribute in attributes:
            key, _, value = attribute.partition("=")
            self.attributes.setdefault(key, value)

    def total(self) -> int:
        return self.end - self.start

    def tokens(self) -> tuple[int, int]:
        read = self.attributes.get
        return int(read("input_tokens", "0")), int(read("output_tokens", "0"))


class _Tree:
    """The spans reachable from a root, each with its depth, its children by (start, id), and
    the roots under the parent id ""."""

    def __init__(self, spans: dict[str, _Span]) -> None:
        self.children: dict[str, list[_Span]] = defaultdict(list)
        for span in spans.values():
            parent = span.parent if span.parent in spans else ""
            self.children[parent].append(span)
        for listed in self.children.values():
            listed.sort(key=lambda span: (span.start, span.id))
        self.preorder: list[tuple[int, _Span]] = []
        stack = [(1, span) for span in reversed(self.children[""])]
        while stack:
            depth, span = stack.pop()
            self.preorder.append((depth, span))
            stack.extend((depth + 1, child) for child in reversed(self.children[span.id]))
        self.depth = {span.id: depth for depth, span in self.preorder}

    def spans(self) -> list[_Span]:
        return [span for _, span in self.preorder]

    def subtree(self, span: _Span) -> list[_Span]:
        found, stack = [], [span]
        while stack:
            current = stack.pop()
            found.append(current)
            stack.extend(self.children[current.id])
        return found


def _rounded(nanos: int) -> int:
    """Nanos (thousandths of a micro) to whole micros, halves up."""
    return (nanos + NANOS_PER_MICRO // 2) // NANOS_PER_MICRO


def _normalized_args(text: str) -> str:
    pairs = []
    for piece in text.split("&"):
        piece = piece.strip(" ")
        if piece:
            name, _, value = piece.partition("=")
            pairs.append((name.strip(" ").lower(), value.strip(" ")))
    return "&".join(f"{name}={value}" for name, value in sorted(pairs))


class TraceAnalyzer:
    def __init__(self) -> None:
        self._events: list[tuple[str, bool]] = []
        self._spans: dict[str, _Span] = {}
        self._prices: dict[str, tuple[int, int]] = {}
        self._cached: _Tree | None = None

    # Level 1
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
        fresh = span_id not in self._spans
        self._events.append((span_id, fresh))
        if fresh:
            self._spans[span_id] = _Span(
                (span_id, parent_id, kind, name, start, end, status), attributes
            )
            self._cached = None
        return fresh

    def errors(self) -> list[list[str]]:
        tree = self._tree()
        rows = []
        for position, (span_id, fresh) in enumerate(self._events):
            codes = []
            if not fresh:
                codes.append(DUPLICATE_ID)
            else:
                span = self._spans[span_id]
                if span.late:
                    codes.append(END_BEFORE_START)
                if span.parent and span.parent not in self._spans:
                    codes.append(UNKNOWN_PARENT)
                if span_id not in tree.depth:
                    codes.append(PARENT_CYCLE)
            rows.extend([str(position), code, span_id] for code in codes)
        return rows

    def outline(self) -> list[list[str]]:
        return [
            [str(depth), span.id, span.kind, span.name] for depth, span in self._tree().preorder
        ]

    def depth(self) -> int:
        return max(self._tree().depth.values(), default=0)

    def kind_counts(self) -> list[list[str]]:
        counts: dict[str, int] = defaultdict(int)
        for span in self._tree().spans():
            counts[span.kind] += 1
        return [[kind, str(counts[kind])] for kind in sorted(counts)]

    # Level 2
    def timing(self, span_id: str) -> list[int]:
        span = self._tree_span(span_id)
        return [] if span is None else [span.total(), self._self_time(span)]

    def critical_path(self) -> list[str]:
        return [span.id for span in self._critical()]

    def slowest(self, n: int) -> list[list[str]]:
        rows = [(self._self_time(span), span.total(), span.id) for span in self._tree().spans()]
        rows.sort(key=lambda row: (-row[0], -row[1], row[2]))
        return [[span_id, str(own), str(total)] for own, total, span_id in rows[:n]]

    # Level 3
    def set_price(self, model: str, input_price: int, output_price: int) -> bool:
        fresh = model not in self._prices
        self._prices[model] = (input_price, output_price)
        return fresh

    def rollup(self, span_id: str) -> list[int]:
        span = self._tree_span(span_id)
        if span is None:
            return []
        own_in, own_out = span.tokens()
        tree_in = tree_out = tree_nanos = 0
        for member in self._tree().subtree(span):
            member_in, member_out = member.tokens()
            tree_in += member_in
            tree_out += member_out
            tree_nanos += self._nanos(member)
        return [
            own_in,
            own_out,
            _rounded(self._nanos(span)),
            tree_in,
            tree_out,
            _rounded(tree_nanos),
        ]

    def cost_by_kind(self) -> list[list[str]]:
        totals: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
        for span in self._tree().spans():
            tokens_in, tokens_out = span.tokens()
            entry = totals[span.kind]
            entry[0] += tokens_in
            entry[1] += tokens_out
            entry[2] += self._nanos(span)
        ordered = sorted(totals.items(), key=lambda item: (-item[1][2], item[0]))
        return [[kind, str(i), str(o), str(_rounded(nanos))] for kind, (i, o, nanos) in ordered]

    def unpriced(self) -> list[str]:
        return sorted(span.id for span in self._tree().spans() if self._is_unpriced(span))

    # Level 4
    def retry_loops(self, min_run: int) -> list[list[str]]:
        tree = self._tree()
        loops: list[list[_Span]] = []
        for siblings in tree.children.values():
            run: list[_Span] = []
            for span in [s for s in siblings if s.kind == "tool" and s.id in tree.depth]:
                if run and span.status == "error" and self._call(span) == self._call(run[0]):
                    run.append(span)
                    continue
                if len(run) >= min_run:
                    loops.append(run)
                run = [span] if span.status == "error" else []
            if len(run) >= min_run:
                loops.append(run)
        loops.sort(key=lambda run: (run[0].start, run[0].id))
        return [
            [run[0].id, run[-1].id, run[0].name, self._call(run[0])[1], str(len(run))]
            for run in loops
        ]

    def root_cause(self) -> list[str]:
        cause = self._root_cause()
        return [] if cause is None else [cause.id, cause.kind, cause.name]

    def report(self, min_run: int) -> list[str]:
        spans = self._tree().spans()
        critical = self._critical()
        cause = self._root_cause()
        loops = self.retry_loops(min_run)
        status = "empty"
        if critical:
            status = "failed" if critical[0].status == "error" else "ok"
        return [
            f"spans: {len(spans)}",
            f"depth: {self.depth()}",
            f"malformed: {len({row[0] for row in self.errors()})}",
            f"status: {status}",
            f"critical path: {len(critical)}",
            f"duration: {critical[0].total() if critical else 0}",
            f"root cause: {cause.id if cause else 'none'}",
            f"retry loops: {len(loops)}",
            f"repeated calls: {sum(int(loop[4]) - 1 for loop in loops)}",
            f"tokens: {sum(sum(span.tokens()) for span in spans)}",
            f"cost: {_rounded(sum(self._nanos(span) for span in spans))}",
            f"unpriced: {len(self.unpriced())}",
        ]

    # Helpers
    def _tree(self) -> _Tree:
        if self._cached is None:
            self._cached = _Tree(self._spans)
        return self._cached

    def _tree_span(self, span_id: str) -> _Span | None:
        return self._spans[span_id] if span_id in self._tree().depth else None

    def _self_time(self, span: _Span) -> int:
        """The span's length minus the union of its children, each clipped to the span."""
        clipped = sorted(
            (max(child.start, span.start), min(child.end, span.end))
            for child in self._tree().children[span.id]
        )
        covered, reach = 0, span.start
        for low, high in clipped:
            low = max(low, reach)
            if high > low:
                covered += high - low
                reach = high
        return span.total() - covered

    def _critical(self) -> list[_Span]:
        tree = self._tree()
        roots = tree.children[""]
        if not roots:
            return []

        def latest_first(span: _Span) -> tuple[int, int, str]:
            return (-span.end, span.start, span.id)

        path: list[_Span] = []
        pending = [min(roots, key=latest_first)]
        while pending:
            span = pending.pop()
            path.append(span)
            # The cursor only moves back, so a child that ends after it now never fits later:
            # one scan of the children, latest end first, finds every pick in turn.
            cursor, chosen = span.end, []
            for child in sorted(tree.children[span.id], key=latest_first):
                if child.end <= cursor:
                    chosen.append(child)
                    cursor = child.start
            pending.extend(chosen)
        return path

    def _root_cause(self) -> _Span | None:
        critical = self._critical()
        if not critical or critical[0].status != "error":
            return None
        depth = self._tree().depth
        failing = [span for span in critical if span.status == "error"]
        return min(failing, key=lambda span: (span.end, -depth[span.id], span.id))

    def _is_unpriced(self, span: _Span) -> bool:
        return sum(span.tokens()) > 0 and span.attributes.get("model") not in self._prices

    def _nanos(self, span: _Span) -> int:
        if sum(span.tokens()) == 0 or self._is_unpriced(span):
            return 0
        price_in, price_out = self._prices[span.attributes["model"]]
        tokens_in, tokens_out = span.tokens()
        return tokens_in * price_in + tokens_out * price_out

    def _call(self, span: _Span) -> tuple[str, str]:
        return span.name, _normalized_args(span.attributes.get("args", ""))
