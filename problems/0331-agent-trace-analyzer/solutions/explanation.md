# Agent Trace Analyzer: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| tree-merge-walk | optimal | O(n log n) per query | O(n) | default answer; one tree, built once per change, serves every level |

Here `n` is the number of events.

## How the design grows level by level

| Level | Change | What the analyzer adds |
|-------|--------|------------------------|
| 1 | From events to a tree | The first event per id, a map from parent to sorted children with lost parents mapped to the roots, and one walk from the roots |
| 2 | Where the time went | An interval sweep per span for self time, and a walk back from each end for the critical path |
| 3 | What it cost | Integer costs in thousandths of a micro, added over a subtree or a kind and rounded once |
| 4 | What went wrong | A normalizer for arguments, a scan for runs among tool siblings, and a choice among the failing spans of the critical path |

The early choice that carries everything is to build the tree from the roots down, once, and to define every later answer on it. Spans whose parents loop are exactly the spans that walk never reaches, so level 1 needs no cycle search, and levels 2 to 4 never see them. The tree is cached and rebuilt only when a new span arrives.

## Approach: tree-merge-walk (Index the spans by parent then merge child intervals and walk back from each end)

### Intuition

A trace is a forest given in pieces. Index the pieces by parent, and every question becomes a walk: down from the roots for the outline and the depth, over a span's children for its self time, back in time from a span's end for the critical path, down a subtree for its cost, along a row of siblings for retry loops, and along the critical path for the root cause. The only arithmetic that needs care is money, which stays an integer until the very end.

### Algorithm

1. `addSpan`: append `(id, fresh)` to the event list. Keep the first event of each id as its span, with `late = end < start` and its end raised to its start when late. Keep the first value of each attribute key.
2. Build the tree: put each span in the child list of its parent when that parent is a span, and in the list under `""` otherwise. Sort each list by `(start, id)`. Walk depth first from the `""` list, recording each span's depth; the spans not reached are left out.
3. `errors`: for each event in order, `duplicate_id` when it was not fresh; otherwise `end_before_start` when late, `unknown_parent` when its parent is not `""` and not a span, and `parent_cycle` when the walk did not reach it.
4. `outline`, `depth` and `kindCounts` read the walk.
5. `timing`: total is `end - start`. For self time, clip each child to `[start, end]`, sort by start, and sweep with the furthest end reached so far, adding only the part of each interval beyond it.
6. `criticalPath`: take the root with the latest end, then the earliest start, then the smallest id. For each span on the path, sort its children by `(-end, start, id)`, set the cursor to the span's end, and scan: a child whose end is at or before the cursor is chosen, and the cursor moves to its start. Then visit the chosen children in time order, each followed by its own path.
7. `rollup` and `costByKind`: the exact cost of a span in thousandths of a micro is `inputTokens * inputPrice + outputTokens * outputPrice`, or 0 when it is unpriced. Add these integers over the subtree or the kind, and round once with `floor((n + 500) / 1000)`. Sort the kinds by the exact sum, largest first, then by name.
8. `retryLoops`: for each list of siblings, keep the tool calls in their `(start, id)` order, and grow a run while each call is an `error` with the same tool and normalized arguments as the run's first call; otherwise flush the run if it is long enough and start again. Flush once more after the last call. Sort the runs by their first span.
9. `rootCause`: if the first span of the critical path has status `error`, choose among the path's failing spans the smallest `(end, -depth, id)`.
10. `report`: the twelve lines, each read from the answers above. The cost line rounds the sum of all exact costs once.

### Correctness

Tree: every span whose chain of parents reaches a root is reached by the walk from the roots, because the walk follows every child list from every root. A span whose chain loops never reaches a root, since following it repeats the loop forever, so no root's walk can reach it, and neither can a span below it. The unreached spans are therefore exactly those of `parent_cycle`, and a span with a lost parent is in the `""` list, so it is a root as the statement says.

Self time: after clipping and sorting by start, an interval adds the length of its part beyond the furthest end seen, which is the length it adds to the union. Every instant covered by a child is counted once, so the result is the total minus the union.

Critical path: the statement repeatedly chooses, among the unchosen children ending at or before the cursor, the one first in the order `(-end, start, id)`. The cursor never increases, because it moves to the start of a child that ends at or before it. A child skipped in the scan ends after the cursor at that moment, so it ends after every later cursor too and can never be chosen. The first child in the scan that fits is therefore the one the statement chooses, and the scan finds each choice in turn.

Costs: the exact cost of a span is a whole number of thousandths of a micro, so adding the integers is exact, and `floor((n + 500) / 1000)` is the nearest whole micro with halves up. A subtree's cost rounds the sum, not the parts.

Retry loops: a run holds consecutive failing tool calls with the call of its first span, so every span added keeps that property, and the run is flushed exactly when the next call breaks it or the siblings end, which makes it as long as possible.

Root cause: a failing span on the path that ends first is the earliest failure the path saw; the tie rule prefers the deeper span, the one that a parent ending at the same instant was waiting on.

### Complexity

- Time: O(n log n) per query — the tree is built with one sort per child list and cached until a span is added; self time sorts each span's children once, which is O(n log n) over all spans; the critical path sorts each child list on it once; costs, runs and the report are linear passes.
- Space: O(n) — the events, the spans, their attributes and the cached tree.

### Trade-offs

- Rebuilding the tree after every new span and caching it suits a trace that is read after it is loaded. A live view that receives spans one at a time would update the child lists in place instead, and would have to move a subtree when a lost parent arrives.
- Treating a span with a lost parent as a root keeps its data visible, which is what an engineer debugging a broken exporter needs. Dropping it would hide cost and time, and attaching it to a guessed parent would invent structure.
- A span that ends before it starts is kept as a zero-length span. That keeps its subtree, and its tokens, in the answers, at the price of trusting neither of its clocks. Shifting it by an estimated clock offset would be more accurate when the offset is known.
- The critical path walks back from each end and follows the last child to finish. It is cheap and explainable, and it says nothing about slack: a sibling that finished one millisecond earlier is just as important in practice. A full slack analysis needs the dependencies between siblings, which a trace does not record.
- Money is an integer until the final rounding, so totals never drift and the two languages always agree. Rounding per span would make every subtree's cost depend on how the spans are grouped.
- Retry loops compare normalized arguments. The normalizer handles order, spacing and the case of names, not semantic equivalence (`city=nyc` and `city=new york`); a stricter rule would compare parsed arguments with a schema.

### Pitfalls and edge cases

- Level 1: only the first event of an id counts; a duplicate gets no other code. A lost parent makes a root, and its children stay below it. The spans below a loop are left out as well as the loop itself, and each gets `parent_cycle`. Errors are sorted by position, and the codes of one event follow the table. Children sort by start, then by id compared by character values, so `a_c` comes before `ab`, and roots sort the same way. The depth of a root is 1. Kinds are counted over the tree only.
- Level 2: overlapping children are merged before subtracting, and each is clipped to its parent; a child entirely outside covers nothing, and grandchildren do not count. A late span is zero long, so its total is 0, never negative. The critical path includes earlier siblings that ended exactly when a chosen one started, excludes a child that ends after its parent, breaks a tie on the end by the earlier start, and lists the children in time order. Zero-length spans can be on the path. The critical root is the one that ends last, not the longest.
- Level 3: round once, halves up, never per span and never to even; 0.499 is 0 and 0.5 is 1. The first `input_tokens` counts when a key repeats. A span with tokens and no model, or a model with no price, is unpriced; a price of 0 is a price. Prices are per 1000 tokens, input and output separately, and a new price replaces the old one. Spans outside the tree cost nothing. Kinds sort by exact cost, so two kinds that round to the same number keep their exact order.
- Level 4: compare normalized arguments: names lowercased, values as written apart from their outer spaces, empty pieces dropped, pairs sorted. Runs are found among tool siblings only, a model call between two tool calls does not break a run, a success ends one, and the last run of a list must be flushed. `minRun` is a minimum, not a bound to exceed. The root cause exists only when the first span of the critical path failed; it is the failing span on the path that ends first, not the first in path order and not a failure off the path. `malformed` counts events, not error rows, and the trace cost rounds the sum of all spans once.

### Language notes

- Python: `str.partition("=")` splits at the first `=` and gives an empty value when there is none. `dict.setdefault` keeps the first attribute and the first event. Tuples such as `(-end, start, id)` give each ordering in one key, and `(n + 500) // 1000` is the rounding on integers of any size. `str.strip(" ")` removes spaces only, which is what the statement asks for.
- TypeScript: numbers are exact for integers below 2^53, which the constraints guarantee for every count and cost, and `Math.floor((n + 500) / 1000)` stays exact there. Sort comparators chain with `||`, and ids compare with `<` and `>` (code unit order), not `localeCompare`, which would put `_` elsewhere. `Map` keeps insertion order and has no inherited keys, so ids such as `constructor` are safe. A span is a class with fields assigned in the constructor, without parameter properties.

## Further reading

- OpenTelemetry, [Tracing API specification](https://opentelemetry.io/docs/specs/otel/trace/api/): a span carries a name, a parent, a span kind, start and end timestamps, attributes, links, events and a status, whose codes are Unset, Ok and Error.
- W3C, [Trace Context](https://www.w3.org/TR/trace-context/), W3C Recommendation, 23 November 2021: how a trace id and the caller's parent id travel between services, so that spans from many services join one trace.
- OpenTelemetry, [semantic conventions for generative AI](https://github.com/open-telemetry/semantic-conventions-genai), in development: model calls record `gen_ai.usage.input_tokens` and `gen_ai.usage.output_tokens`, and tool calls are spans with the operation `execute_tool`, the attribute `gen_ai.tool.name` and, opt-in, `gen_ai.tool.call.arguments`.
- J. E. Kelley Jr. and M. R. Walker, "Critical-path planning and scheduling", Papers presented at the eastern joint IRE-AIEE-ACM computer conference, December 1959, pp. 160-173, doi:10.1145/1460299.1460318: critical-path planning of project schedules, the idea that level 2 applies to a trace.
- S. Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models", arXiv:2210.03629 (the version published at ICLR): a model that interleaves reasoning traces with actions that reach external sources such as knowledge bases, the kind of run whose traces this problem reads.
