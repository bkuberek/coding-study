# Debug: Nil Map Write: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| create-on-write | optimal | O(1) per record, O(v) per views or merge | O(d) | default answer: every write path creates the inner map first |

## Approach: create-on-write (Create the inner map before writing to it)

### Intuition

Indexing a map with a missing key returns the zero value of the element type. For `map[string]map[string]int` that zero value is a nil map. A nil map is a perfectly good *read-only* empty map: `len` returns 0, `range` runs zero times, and a lookup returns 0. Writing to it panics with `assignment to entry in nil map`.

`Views` and `UniqueVisitors` only read, so a missing page quietly reports 0, which is exactly the behavior the statement asks for. That success is what makes the bug easy to miss. `Merge` reads `into := p.visits[target]` the same way and then *writes* `into[visitor] += count`. When `target` already has views, `into` is a real map and the merge works, as it did for `/faq` and `/help`. When `target` is a new address, as `/plans` was, `into` is nil and the first write panics.

Even without the panic, writing into the inner map would not be enough: the new map must also be stored in `p.visits[target]`, or the merged views vanish with the local variable. `Record` already does both, so the fix is to share that code.

### Debugging approach

1. **Read the panic.** The runner reports `assignment to entry in nil map` from `Merge`. Only one statement in `Merge` assigns to a map entry: `into[visitor] += count`.
2. **Find the input class.** Merges into pages that have views pass; merges into new pages fail (`h1`, `h6`, `h10`). Merges *from* a missing page pass too, because ranging over a nil map writes nothing.
3. **Inspect the value.** `fmt.Printf("%#v\n", into)` prints `map[string]int(nil)` for a new target. A nil map prints as `map[]` with `%v`, the same as an empty one, which is why plain `%v` debugging can mislead.
4. **Compare with the working write path.** `Record` looks the page up with the comma-ok form, and creates and stores the inner map when it is missing. `Merge` skipped that step.

### Algorithm

1. `visitorsOf(page)` looks the page up; if it is missing, it creates an empty inner map and stores it under `page`. It returns the inner map.
2. `Record(page, visitor)` increments `visitorsOf(page)[visitor]`.
3. `Views(page)` sums the inner map's counts; `UniqueVisitors(page)` returns its length. Both read only, so a missing page reads as an empty map.
4. `Merge(source, target)`: if `source` has no views or equals `target`, return. Otherwise add each of its counts to `visitorsOf(target)` and delete `source`.

### Correctness

Every write goes through `visitorsOf`, which returns a non-nil map stored in `p.visits`, so no write can hit a nil map and every write is visible to later reads. `Merge` adds each `(visitor, count)` of `source` to the same visitor in `target`, so `Views(target)` grows by `Views(source)` and the distinct visitors of `target` become the union of both sets. Deleting `source` makes it read as an empty map afterwards. Merging a page into itself returns before deleting anything, so it changes nothing; without that check, adding the counts to themselves and then deleting the page would lose all of its views.

### Complexity

- Time: O(1) per record, O(v) per views or merge — `Record` and `UniqueVisitors` are a few hash operations; `Views` and `Merge` visit the v visitors of one page.
- Space: O(d) — one counter for each distinct pair of page and visitor.

### Trade-offs

A helper that creates on first write keeps the rule in one place, so a future write path (for example "delete a visitor's views") cannot forget it. The alternatives are weaker. Creating the target map inline in `Merge` works but duplicates `Record`'s code. Checking `if into == nil` alone is not enough: the new map must be stored back into `p.visits`. A flat `map[pageVisitor]int` keyed by a struct removes the inner maps altogether and with them this bug, but `UniqueVisitors` and `Merge` then scan every entry or need a second index.

### Pitfalls and edge cases

- The general trap: a nil map, the zero value of a map type, can be read but not written. A missing key in a map of maps returns such a nil map, and so does a struct field that nobody initialized.
- `into := p.visits[target]; if into == nil { into = make(map[string]int) }` stops the panic but loses the merged views, because the new map is never stored.
- Merging a page into itself must not delete it. Check `source == target` before deleting.
- Merging a missing source must not create an empty target entry that later code might treat as a real page; returning early avoids it.
- Deleting from a nil map and ranging over one are both safe, so code paths that only delete or read never reveal the problem.

### Prevention

- Funnel every write to a nested map through one accessor that creates the inner map.
- Make zero values useful or impossible: either initialize maps in the constructor and in every place that adds a key, or document that a type must be created with its `New` function.
- Test write paths with keys that do not exist yet, not only with keys an earlier step created.

### Language notes

- Go only. In Java and Kotlin, `get` on a missing key returns `null`, which fails on reads and writes alike (`NullPointerException` in Java; Kotlin's nullable type does not even compile without a check), so the read paths force the same decision the write path needs. Python's `dict[key]` raises `KeyError` on reads and writes alike, and `defaultdict` creates the inner dict on any access. TypeScript's `Map.get` returns `undefined`, which the type checker makes callers handle. Go is the language where a missing nested map reads as empty and fails only on write.
- `map[string]int(nil)` and `map[string]int{}` print the same with `%v`. Use `%#v`, or a debugger, to tell them apart.
