# Agent Trace Analyzer

## Statement

Build `TraceAnalyzer`, the tool you open when an AI agent took too long, cost too much or gave up, and you need to know why. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**What is a trace?** An agent answers a request in many steps: it calls a language model to plan, calls tools (a search, a database, an API), retrieves documents, calls the model again, and so on, often with steps inside steps. A *trace* records one request as a set of **spans**. A span is one step: it has an id, the id of the step it ran inside (its *parent*, none for the first step), a start and an end time, and a status that says whether it succeeded. Because each span names its parent, the spans form a tree: the request at the top, its steps below it, their steps below them. *Attributes*, small `key=value` facts such as the model used or the tokens it read, describe a span further.

This is the shape of an open standard, OpenTelemetry, whose spans carry a name, a parent, start and end timestamps, attributes and a status (see the explanation's further reading). Tracing systems export spans as they finish, so a child, which ends first, usually arrives before its parent, and the events of one request can come in any order, be repeated, or point to a parent that was never received. This problem reads such a list of events and answers the questions an engineer asks of it: what ran inside what, where the time went, what it cost, and what went wrong first.

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 35, level 2 by 65, level 3 by 85 and level 4 by 115, keeping the last minutes for a final run.

## Input

- `TraceAnalyzer()`: creates an empty analyzer.
- A span id is 1 to 16 characters from `a` to `z`, `0` to `9` and `_`. Ids, kinds and names are compared by the numeric value of their characters, so digits come before `_`, which comes before letters.
- `parentId` is `""` for a span that has no parent, or a span id.
- `kind` is the type of the step, 1 to 20 characters from `a` to `z` and `_`, such as `agent`, `model`, `tool` or `retrieval`. (OpenTelemetry has a field named *span kind* with another meaning: whether a span serves a remote request, makes one, produces or consumes a message, or is internal work. This problem does not use it.)
- `name` is 1 to 30 characters from `a` to `z`, `0` to `9`, `_` and `.`.
- `start` and `end` are times in milliseconds, integers from 0 to 10^9.
- `status` is `ok`, `error` or `unset`, as in OpenTelemetry.
- `attributes` is a list of 0 to 10 strings, each `key=value`: the key is everything before the first `=`, 1 to 30 characters from `a` to `z`, `_` and `.`, and the value everything after it, 0 to 100 characters from the space to `~` in ASCII. When a key appears more than once, the first one counts, unlike OpenTelemetry's attribute setter, where setting an existing key overwrites its value. A level that reads an attribute names it; the others are ignored.
- Each level's section describes the methods it adds and their parameters.

## Output

Spans and findings come back as rows of text, as described by each method. Numbers in rows are written in decimal as text.

## Level 1: From events to a tree

- `addSpan(spanId, parentId, kind, name, start, end, status, attributes)`: records an event. Events are numbered by **position**, 0 for the first one added, 1 for the next, and so on. It returns `false` when an earlier event already used `spanId`, and `true` otherwise.
- `errors()`: the malformed events, as rows `[position, code, spanId]`.
- `outline()`: the tree, as rows `[depth, spanId, kind, name]`.
- `depth()`: the largest depth in the tree, and 0 when the tree is empty.
- `kindCounts()`: the number of spans of each kind in the tree, as rows `[kind, count]`, sorted by kind.

**The spans and the tree.** The first event with a given id is that id's **span**; a later event with the same id is a duplicate and is ignored except in `errors()`. A span is a **root** when its `parentId` is `""`, or when no span has the id `parentId` (its parent was lost: it is kept, as the top of a tree of its own). Every other span sits under its parent. A span whose chain of parents never reaches a root, because it loops (`a` under `b` and `b` under `a`, or a span that is its own parent), is left out of the tree, together with every span below it. The **tree** is the set of spans that are left. A root has depth 1, and a span under a parent of depth `d` has depth `d + 1`. A parent may arrive after its children: what matters is the set of events, not their order.

**Errors.** Each event gets the codes that apply to it, from this list, in this order:

| Code | The event |
|------|-----------|
| `duplicate_id` | uses a span id that an earlier event used (it gets no other code) |
| `end_before_start` | has `end < start`; its span stays in the tree |
| `unknown_parent` | has a `parentId` that is not `""` and that no span has; its span stays in the tree as a root |
| `parent_cycle` | is a span left out of the tree because its parents loop |

The rows are sorted by position, and the codes of one event come in the order of the table.

**The outline** lists the tree depth first: each root, then everything below it, before the next root. The roots, and the children of each span, come in order of `start`, and then of id.

### Example 1

<!-- case: ex1 -->

The events arrive as they were exported: `r1` first, before its parent `t1`, and the root `run` fourth. The tree does not depend on that order. The outline starts at `run`, then lists its children by start time: `m1` at 10, `t1` at 210 with `r1` below it, and `m2` at 410. The deepest chain is `run`, `t1`, `r1`, so the depth is 3. Nothing is malformed.

### Example 2

<!-- case: ex2 -->

`b` ends before it starts and stays in the tree. `c` names a parent, `ghost`, that never arrived, so it becomes a root, and its child `h` stays below it. The second `a` is a duplicate and is ignored; the first `a` stands. `d` and `e` are each other's parent and `g` is its own, so following their parents never reaches a root; they are left out, and so is `f`, which hangs below the loop. The errors come by position, and the 4 spans left are counted by kind.

## Level 2: Where the time went

A slow request is rarely slow everywhere. This level tells the time a span spent itself from the time it waited on its children, and finds the chain of steps that set the length of the whole request.

- `timing(spanId)`: `[total, self]` for a span of the tree, and `[]` for any other id.
- `criticalPath()`: the ids of the spans on the critical path, in the order described below.
- `slowest(n)`: the `n` spans of the tree with the largest self time (all of them when there are fewer), as rows `[spanId, self, total]`. Ties go to the larger total, then to the smaller id.

**End.** A span reported as `end_before_start` counts as taking no time: its end is its start. Everywhere below, "end" means this end.

**Total and self time.** The **total** time of a span is `end - start`. Its **self** time is the total minus the time during which at least one of its children was running. Children can overlap (an agent may call three tools at once), so their intervals are merged first, and each child's interval is clipped to the span's own interval first, since a child may start before or end after its parent (clocks drift, and some work outlives the step that started it). A child entirely outside the span covers nothing. Only the span's own children count, not their descendants.

**Critical path.** The critical path is the chain of spans that the request waited on. It starts at a root: the one with the latest end, then the earliest start, then the smallest id. For a span on the path, walk back from its end:

1. The **cursor** starts at the span's end.
2. Among its children that end at or before the cursor and are not chosen yet, choose the one with the latest end; on a tie, the earliest start, then the smallest id. That child held the span up until its end.
3. Move the cursor to the start of the chosen child, and repeat step 2 until no child ends at or before the cursor.

A child that ends after the cursor overlapped one that was already chosen, so it ran alongside and did not hold anything up. A child that ends exactly when a chosen one starts did hold it up, since the next step began only when it was done. The path lists each span, then the path of each of its chosen children in order of time (the last one chosen first), each followed by its own chosen children, and so on.

### Example 1

<!-- case: ex3 -->

`a` (10 to 40) and `b` (30 to 60) overlap, so together they cover 10 to 60, 50 ms, and `c` covers 10 more: `root` spent 100 - 60 = 40 ms itself. `a1` runs past the end of `a`, so only 20 to 40 of it counts against `a`, which keeps 10 ms of its own. Walking back from 100, `c` ends last, at 80; before `c` starts, at 70, `b` ends last, at 60; before `b` starts, at 30, no child has ended, since `a` ran alongside `b`. `a1` and `b` tie on self and total time, and the smaller id comes first. An unknown id has no timing.

### Example 2

<!-- case: ex4 -->

Three tools run in parallel, then the model `m` runs from 200 to 450, and `bg`, an upload, runs on until 700, past the end of `main`. Walking back from 500, `bg` ends too late to have held `main` up; `m` ends last, then `p2`, which ends exactly when `m` starts, while `p1` and `p3` ran alongside `p2`. Inside `m`, `skew` ends before it starts, so it takes no time at 300, and `zero` takes no time at 260: both end before the cursor, so both are on the path, adding nothing to its length. `main` spent no time itself, since its children cover all of it. `lost` lost its parent and is a root, but `main` ends later.

## Level 3: What it cost

Each model call reads and writes tokens, and a provider charges for them. This level adds the costs up the tree, so that a step's cost includes everything that ran inside it.

- `setPrice(model, inputPrice, outputPrice)`: sets the price of a model, in micros (millionths of a currency unit) per 1000 input tokens and per 1000 output tokens. It returns `true` when the model had no price, and `false` when it replaces an earlier price. Prices apply to every span, whenever its event was added.
- `rollup(spanId)`: for a span of the tree, `[inputTokens, outputTokens, cost, subtreeInputTokens, subtreeOutputTokens, subtreeCost]`, where the subtree is the span and every span below it in the tree; `[]` for any other id.
- `costByKind()`: one row `[kind, inputTokens, outputTokens, cost]` per kind of span in the tree, sorted by exact cost (below), largest first, then by kind.
- `unpriced()`: the ids of the unpriced spans of the tree, sorted.

**Tokens and models.** A span's tokens are read from the attributes `input_tokens` and `output_tokens`, each an integer from 0 to 10^6 written in decimal, and are 0 when missing. Its model is the attribute `model`. (OpenTelemetry's conventions for generative AI name the token counts `gen_ai.usage.input_tokens` and `gen_ai.usage.output_tokens`; the short keys keep the cases readable.) A span that has tokens (more than 0 in all) is **unpriced** when it has no `model` attribute or its model has no price; its cost is 0, and it is listed, so that a missing price cannot quietly lower the total. A price of 0 is a price.

**Cost and rounding.** The exact cost of a span is `(inputTokens * inputPrice + outputTokens * outputPrice) / 1000` micros, which may have a fraction. Costs are added exactly, and a reported cost is rounded once, at the end, to a whole number of micros, halves up: 2.5 becomes 3, 2.4 becomes 2. The cost of a subtree or a kind is the rounded sum of the exact costs of its spans, which can differ from the sum of their rounded costs. (Working in thousandths of a micro, `n`, the rounded cost is `floor((n + 500) / 1000)`.)

### Example 1

<!-- case: ex5 -->

`plan` reads 1200 tokens and writes 300 on `small`: 1200 * 150 + 300 * 600 = 360000 thousandths, 360 micros. Each embedding reads 2 tokens at 250 per 1000, half a micro, which rounds up to 1. Together they cost exactly 1 micro, so `search`'s subtree costs 1, not 1 + 1. The whole request costs 18361. `agent` and `tool` spans cost nothing and come last, by name. After the price of `small` changes, which returns `false`, `plan` costs 240.

### Example 2

<!-- case: ex6 -->

`m1` names a model with no price and `m2` names none, so both are unpriced and cost 0. `m3` costs 2.5 micros, which rounds to 3, and the `guard` span costs 1.7, which rounds to 2, but the subtree of `a` costs 4.2, which rounds to 4. Once `mystery` has a price of 0, `m1` is priced and still costs nothing.

## Level 4: What went wrong

An agent that fails often fails the same way several times: it calls a tool, the call fails, the model asks for the same call again, and so on until something gives up. This level finds those loops and the failure that started the trouble.

- `retryLoops(minRun)`: the retry loops of at least `minRun` calls, as rows `[firstSpanId, lastSpanId, name, args, count]`, sorted by the start of their first span, then by its id.
- `rootCause()`: the probable root cause, as `[spanId, kind, name]`, or `[]` when the request did not fail.
- `report(minRun)`: a summary, as the lines described below.

**Calls and arguments.** A *tool call* is a span of the tree whose kind is `tool`. Its tool is its `name`, and its arguments are the attribute `args` (`""` when missing), a list of `name=value` pairs joined by `&`, as in `q=paris&lang=en`. The same arguments can be written in many ways, so they are compared after **normalizing** them:

1. Split the text on every `&`.
2. Remove the spaces at both ends of each piece, and drop the pieces left empty.
3. Split each piece at its first `=` into a name and a value (a piece with no `=` is a name with the value `""`). Remove the spaces at both ends of each, and write the name in lowercase. The value keeps its case and its inner spaces.
4. Sort the pairs by name, then by value, and join them back as `name=value` with `&`.

So ` Q = paris ` and `q=paris` are the same, and so are `lang=en&q=paris` and `q=paris&lang=en`, while `q=Paris` is different.

**Retry loops.** Two spans are *siblings* when they have the same parent in the tree; all roots are siblings of each other. For each set of siblings, take its tool calls in order of start, then id, ignoring the siblings of other kinds. A **retry loop** is a run of consecutive calls in that order whose status is `error` and that have the same tool and the same normalized arguments, as long as it can be: it ends at a call whose status is not `error`, such as a retry that succeeded, or at a call to another tool or with other arguments. A run is reported when it has at least `minRun` calls; `args` is the normalized arguments.

**Root cause.** The request **failed** when the first span of the critical path has status `error`. Then the root cause is the span on the critical path with status `error` that ends first, since a failure is known when its span ends, and the spans above it usually fail because it did; on a tie, the deeper span, then the smaller id. A failure off the critical path, or in a request that did not fail, is not a root cause.

**Report.** These 12 lines, in order:

```text
spans: <the number of spans in the tree>
depth: <depth()>
malformed: <the number of events with at least one error>
status: <`empty` when the tree is empty, `failed` when the request failed, else `ok`>
critical path: <the number of spans on the critical path>
duration: <the total time of the first span of the critical path, 0 when there is none>
root cause: <the id of the root cause, or `none`>
retry loops: <the number of retry loops of at least minRun calls>
repeated calls: <the sum over those loops of count - 1>
tokens: <all input and output tokens of the tree>
cost: <the rounded sum of the exact costs of all spans of the tree>
unpriced: <the number of unpriced spans>
```

Each `<...>` is replaced by its value. The words in backticks, `empty`, `failed`, `ok` and `none`, are printed literally, without the backticks: an empty trace gives `status: empty` and `root cause: none`.

### Example 1

<!-- case: ex7 -->

The agent called `search` five times and every call failed. `t1`, `t2` and `t3` ask for `q=paris` written three ways, so they are one loop of 3; the model calls between them are not tool calls and do not break it. `t4` changes the arguments and starts a new run, and `t5` has the same pairs in another order, a loop of 2. The steps ran one after another, so the whole trace is the critical path. The request failed, and the failure that ended first on the path is `t1`, the first search.

### Example 2

<!-- case: ex8 -->

`f1` and `f2` fail with the same arguments in two orders, a loop of 2, and `f3` succeeds with them, which ends the run. The request succeeded, so there is no root cause, although two calls failed: the agent recovered. The model call costs 900 * 150 + 100 * 600 = 195000 thousandths, 195 micros. With `minRun` 3 there is no loop.

## Constraints

- At most 2000 calls per test and at most 1000 events.
- Prices are integers from 0 to 10^5. `n` is from 1 to 50, and `minRun` from 2 to 10.
- Every count and cost fits in 2^53 - 1.

## Follow-ups

- Here the whole trace is loaded before it is read. A live system receives spans for minutes after a request starts. Which answers can you give while spans are still arriving, and which have to wait until you know the trace is complete?
- A lost parent becomes a root. When the parent arrives later, the tree changes, and so may the critical path and the root cause. How would you report results that may still change?
- The critical path follows the last child to finish. Two parallel calls that finish within a millisecond of each other both nearly held the parent up. How would you show how much slack each step had, and which steps would make the request faster if they were faster?
- Prices change, and a long trace may cross a price change. What would you store with each span so that a cost computed later matches the bill?
- A retry loop is found after the fact. What signal would let an agent stop itself after the second identical failure, and what would it do instead of a third call?
- A trace can hold prompts, tool arguments and documents. Which attributes would you keep, which would you redact, and who should be able to read the rest?

## Hints

### Hint 1

Start by turning the list into a dictionary from id to span, keeping only the first event of each id, and a dictionary from parent id to the list of its children. Put the spans whose parent is `""` or unknown under one key of their own, such as `""`: those are the roots. Everything in level 1 is then a walk from the roots down.

### Hint 2

A span whose parents loop is never reached by that walk, and neither is anything below it. So you do not need to look for loops: the spans the walk from the roots does not reach are exactly the ones to report as `parent_cycle`. Sort each list of children by `(start, id)` once, and the outline is a depth-first walk.

### Hint 3

For self time, clip each child's interval to the span's, sort the intervals by start, and sweep them, keeping the furthest end seen so far: each interval adds only the part beyond that end. The critical path needs no search either: walking back, the cursor only moves earlier, so you can sort the children by latest end first once and take each one that ends at or before the cursor.

### Hint 4

Keep money as an integer in thousandths of a micro: `tokens * pricePer1000` is exactly that. Add the integers, and round only the total, with `(n + 500) // 1000`. Rounding each span first and adding the results is the mistake that the rounding rule is there to catch.

### Hint 5

Normalize the arguments with the four steps in order, and compare each tool call with the first call of the current run. A run is flushed when the next call breaks it, and once more after the last call of the siblings, which is easy to forget.

### Hint 6

For the root cause, take the critical path you already have, keep its spans with status `error`, and choose the smallest `(end, -depth, id)`. The first failing span in the order of the path is the top of the trace, which failed only because something below it did.
