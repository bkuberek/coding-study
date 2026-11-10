# Context Packer: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| rank-then-fill | optimal | O(n log n + n k w) per pack | O(n w) | default answer; every level adds one key or one check to the same walk |

Here `n` is the number of stored items, `k` the number of items the collapse keeps, and `w` the number of words in a text.

## How the design grows level by level

| Level | Change | What the walk adds |
|-------|--------|--------------------|
| 1 | Fill a budget greedily | Sort by `(-score, tokens, id)`; take each item that fits, skip the rest |
| 2 | Pinned items always go first | A first sort key, "pinned first", and a check of the pinned total before the walk |
| 3 | Caps per category | A count of items taken per category, checked before taking an unpinned item |
| 4 | Collapse near-duplicates | A pass over the sorted list before the walk that keeps an item only when it is not a near-duplicate of one kept earlier |

One sorted list carries the whole problem. Every rule is either a sort key (score, size, id, pin) or a check made while walking that list once (budget, cap, near-duplicate). Writing level 1 as "sort, then walk" rather than as a loop that picks the best remaining item each time means each later level is one more key or one more check.

## Approach: rank-then-fill (Rank once then fill greedily)

### Intuition

The packer never searches for the best combination: the statement defines the answer as a greedy walk in a fixed order. So the work is to get that order exactly right and to apply each rule at the right moment of the walk. Pins change the order (they come first) and add a precondition (their total must fit). Caps add a counter. Near-duplicates are a filter that runs before the walk, over the same order, because "keep the higher score" is the same as "keep the one that comes first in packing order".

### Algorithm

1. Keep `items`, a map from id to `Item(words, tokens, score, pinned, category)`, where `words` is the set of distinct words of the text, and `caps`, a map from category to its cap.
2. Sort the items by `(not pinned, -score, tokens, id)`.
3. Collapse: walk the sorted items with an empty `kept` list. An unpinned item that is a near-duplicate of some item in `kept` is knocked out, and the first such item in `kept` is recorded as its keeper; every other item is appended to `kept`. Two items are near-duplicates when `5 * shared > 4 * union`, with `shared` the size of the intersection of their word sets and `union = |a| + |b| - shared`.
4. If the pinned items of `kept` need more than `budget` tokens in total, return `["OVER_BUDGET"]`.
5. Walk `kept` with `remaining = budget` and a count of items taken per category. Take a pinned item always. Take an unpinned item when `tokens <= remaining` and its category has no cap or fewer taken than the cap; otherwise skip it. Every taken item lowers `remaining` and raises its category's count.
6. `pin`, `unpin`, `setCategory` and `setCap` only change fields; `duplicateOf` runs the collapse and reads the recorded keeper.

### Correctness

The sort key orders pinned items before unpinned ones and, inside each group, by the packing order of level 1, so walking the sorted list visits items in exactly the order the statement prescribes. The walk takes an unpinned item exactly when the statement does: it fits in what is left and its category has room, where both quantities count only items already taken, which are the items earlier in the order. Pinned items come first, so when their total fits, `remaining` never goes negative while they are taken, and they count toward their categories' caps before any unpinned item is considered. The collapse visits the same order, so for any two near-duplicates the one visited first has the higher score, or the same score and fewer tokens, or the smaller id: it is the one the statement keeps. Comparing a new item only with kept items is what makes "only kept items knock items out" hold, and running the collapse before the walk is what makes it ignore the budget and the caps. The integer test `5 * shared > 4 * union` is the same as `shared / union > 0.8` because `union` is positive.

### Complexity

- Time: O(n log n + n k w) per pack — one sort, then each item is compared with at most the `k` kept items, each comparison costing O(w) set lookups; the walk itself is O(n).
- Space: O(n w) — the word sets of the stored items, plus O(n) for the sorted list and the counters of one pack.

### Trade-offs

- An exact choice (a 0/1 knapsack over tokens) can fill the budget better than the greedy walk, at O(n * budget) time per pack. The statement defines the greedy answer, which is also what context builders usually do: it is predictable, and the order says why an item is in or out.
- Keeping the items sorted between calls (a sorted list or a balanced tree) saves the sort on each `pack`, but every `pin` and `addItem` then has to move items. With 100 items, sorting per call is cheaper to write and fast enough.
- Comparing each item only with the kept ones costs O(n k w); with thousands of items, MinHash signatures or an index from word to items would find candidate near-duplicates without comparing every pair. Mention them when the follow-up asks for scale.

### Pitfalls and edge cases

- Level 1: skip an item that does not fit and keep walking; stopping at the first misfit loses smaller items that still fit. `tokens <= remaining` fits, so a budget equal to the tokens takes the item. Break equal scores by fewer tokens, then by id in string order (`m10` before `m2`). A failed `addItem` must not overwrite the stored item.
- Level 2: pins go in before every unpinned item and in packing order among themselves, not in the order they were pinned. Pins that use exactly the budget pass; one token more returns `["OVER_BUDGET"]`. A budget of 0 with no pins is an empty pack, not a failure. Removing an item drops its pin.
- Level 3: pinned items count toward their category's cap but are never left out for it. An item skipped for the budget must not use a place in its cap. `setCategory` moves an item; it does not add a second category.
- Level 4: the threshold is strict: a similarity of exactly 0.8 (4 shared words out of 5) is not a duplicate. Build word sets, so order and repeats do not matter. Compare only with kept items: when `x` knocks out `y`, an item similar to `y` but not to `x` stays. Collapse before the budget: a large item that does not fit still knocks out its smaller duplicate. Pinned items are never knocked out, and they do knock out unpinned items with a higher score.

### Language notes

- Python: sorting by a key method that returns the tuple `(not pinned, -score, tokens, id)` gives every tie-break in one place, and `False` sorts before `True`. `Counter` returns 0 for a category it has not seen, so the cap check needs no default. `next(..., None)` finds the first keeper and stops there.
- TypeScript: the comparator puts pinned items first explicitly, then chains the numeric keys with `||` and compares ids with `<` and `>`, which match the other language for ASCII; `localeCompare` would not. `Array.prototype.find` returns the first keeper, or `undefined` when there is none.
