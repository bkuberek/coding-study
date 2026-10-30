# All Possible Recipes: Explanation

## Overview

R is the number of recipes, I the total number of ingredient entries and S the number of supplies. Think of a graph with an arrow from every ingredient to each recipe that uses it: a recipe can be prepared exactly when every arrow into it comes from something that can be obtained, which is what a topological sort started from the supplies discovers.

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| sweep-until-stable | brute | O(R * I + S) | O(R + I + S) | the first idea; fine when dependency chains are short |
| kahn | optimal | O(R + I + S) | O(R + I + S) | default answer: each ingredient entry is handled once |
| memo-dfs | optimal | O(R + I + S) | O(R + I + S) | you prefer asking "can I make this?" recursively |

## Approach: sweep-until-stable (Sweep over the recipes until a sweep prepares nothing new)

### Intuition

Keep a set of everything available. Go through the recipes and prepare every one whose ingredients are all in the set, adding it to the set. A recipe that was not ready may become ready after another one is prepared, so sweep again, and stop when a sweep prepares nothing.

### Algorithm

1. Put the supplies into a set `available`; mark every recipe pending.
2. Repeat until a sweep changes nothing: for each pending recipe, if all its ingredients are in `available`, add it to `available` and to the answer.
3. Return the answer.

### Correctness

Everything added to `available` is a supply or a recipe whose ingredients were all available, so every reported recipe can really be prepared, in the order it was added. Conversely, suppose a recipe can be prepared, through some order of preparations. By induction along that order, each recipe in it is added in some sweep: once its ingredients are available, the next sweep adds it. The loop stops only after a sweep that adds nothing, so no preparable recipe is left out. Recipes in a loop or behind a missing item never get all their ingredients, so they are never added.

### Complexity

- Time: O(R * I + S) — each sweep checks every pending recipe's ingredients, O(I) in total, and each sweep except the last prepares at least one recipe, so there are at most R + 1 sweeps; building the set costs O(S).
- Space: O(R + I + S) — the set of available names and the pending list, besides the input.

### Trade-offs

Hard to get wrong, so it serves as the oracle. When recipes form long chains listed in an unlucky order, each sweep adds only a few links and the work grows quadratically. Kahn's algorithm records, for each recipe, how many ingredients are still missing, so it never rechecks a recipe whose situation has not changed.

### Pitfalls and edge cases

- Stop on a sweep with no change, not after a fixed number of sweeps.
- An ingredient that is neither a supply nor a recipe simply never becomes available; it needs no special handling.

### Language notes

- Python: `all(item in available for item in ...)` stops at the first missing item.
- TypeScript: `Set.has` inside `every` does the same.
- Java: `available.containsAll(list)` checks a whole ingredient list in one call.
- Kotlin: `partition` splits the pending recipes into ready and not ready against the items available when the sweep starts, so it may need a few more sweeps than the in-place loop; the result is the same.
- Go: `available` is a `map[string]bool` set, so a missing item reads as `false`, and `allAvailable` stands in for Python's `all(...)` over a generator. A nil slice starts `stillPending`, which `append` grows only when a recipe has to wait.
- Rust: `available` is a `HashSet<&str>` whose members borrow from `supplies` and later `recipes`, so no string is copied while the set grows. `for i in pending` consumes the index list, and `still_pending` is built fresh each sweep, as in the Python version. The result clones each recipe name once, when it is prepared.

## Approach: kahn (Queue available items and count each recipe's missing ingredients)

### Intuition

Each recipe waits for a fixed number of ingredients. Whenever an item becomes available, only the recipes that use it get one step closer. So keep a queue of newly available items, starting with the supplies; each item taken from the queue decrements the missing count of the recipes that use it, and a recipe whose count reaches zero is prepared and becomes a newly available item itself.

### Algorithm

1. For every ingredient entry, record which recipe uses the item (`usedBy[item]`), and set `missing[i]` to the length of `ingredients[i]`.
2. Put all supplies into a queue.
3. While the queue is not empty: take an item; for each recipe `i` in `usedBy[item]`, decrement `missing[i]`, and when it reaches 0, record `recipes[i]` and add it to the queue.
4. Return the recorded recipes.

### Correctness

Every item enters the queue at most once: supplies are distinct, and a recipe's count reaches zero only once. A recipe's count reaches zero exactly when every one of its ingredients has left the queue, that is, when all of them are available; so every recorded recipe can be prepared. If a recipe can be prepared, induction on the order of preparation shows that each of its ingredients eventually enters the queue, so its count reaches zero. Recipes on a loop wait for each other and never reach zero, and neither does a recipe with an ingredient that never enters the queue.

### Complexity

- Time: O(R + I + S) — building `usedBy` and `missing` reads every ingredient entry once; every supply and every prepared recipe is dequeued once, and each ingredient entry causes at most one decrement.
- Space: O(R + I + S) — `usedBy` holds one entry per ingredient entry, plus the counters and the queue.

### Trade-offs

Linear and iterative: the standard topological sort with the supplies as the starting sources. It processes items that no recipe uses (they cost one lookup each) and needs a map keyed by names. The order in which recipes are recorded is a valid preparation order.

### Pitfalls and edge cases

- Count each recipe's ingredients, not its distinct prerequisite recipes: supplies count too, and they are decremented when the supplies are dequeued.
- A recipe that lists itself waits for its own preparation forever, which the counts handle with no special case.

### Language notes

- Python: `defaultdict(list)` builds `used_by`, and `deque` gives O(1) `popleft`.
- TypeScript: `usedBy.get(item) ?? []` handles items that no recipe uses; a moving head index makes the array a queue.
- Java: `computeIfAbsent` builds the lists, and `getOrDefault(item, List.of())` reads them safely.
- Kotlin: `getOrPut` builds the lists, and `orEmpty()` turns a missing entry into an empty list.
- Go: the queue starts as a copy of `supplies` (`append([]string(nil), supplies...)`), so popping the front never disturbs the input slice, and a missing key in `usedBy` reads as an empty slice, which replaces `defaultdict`.
- Rust: `used_by` maps each item to the recipes that use it, borrowing the item names from `ingredients`, and `entry(item).or_default()` plays the part of `defaultdict`. The queue is a `VecDeque<&str>` of names borrowed from `supplies` and `recipes`, so a prepared recipe is pushed without a copy. `let Some(users) = used_by.get(item) else { continue }` skips supplies that no recipe uses.

## Approach: memo-dfs (Memoized depth-first search that treats a loop as impossible)

### Intuition

Ask the question directly: can this item be obtained? A supply can; a name that is neither a supply nor a recipe cannot; a recipe can exactly when all its ingredients can. Memoize the answers. If, while working out a recipe, the search comes back to the same recipe, its ingredients depend on itself, which can never be satisfied, so the answer for that path is "no".

### Algorithm

1. Map each recipe to its ingredients, and put the supplies in a set.
2. `canPrepare(item)`: return `true` for a supply, `false` for an unknown name, `false` for a recipe currently marked `ON_PATH`, and the stored verdict for a decided recipe. Otherwise mark it `ON_PATH`, compute whether all its ingredients can be prepared, store that verdict and return it.
3. Return the recipes for which `canPrepare` is `true`.

### Correctness

For a recipe outside any loop, the recursion evaluates the definition "all ingredients obtainable" over a finite dependency tree, so by induction its verdict is right. Meeting an `ON_PATH` recipe means the current chain of recipes, each needing the next, returns to its start: every recipe on that chain needs, indirectly, itself, so none of them can ever be prepared, and `false` is correct for all of them. Because a recipe needs all of its ingredients, one impossible ingredient makes it impossible, so storing these `false` verdicts never hides a way to prepare it.

### Complexity

- Time: O(R + I + S) — each recipe is expanded once, reading its ingredient list once; every later visit is a lookup.
- Space: O(R + I + S) — the maps and sets, and a recursion depth of at most R.

### Trade-offs

Same bound as Kahn's algorithm and closer to the problem's wording. Its recursion can be as deep as the longest chain of recipes (up to 1000 here), and the cycle reasoning relies on recipes needing all of their ingredients: in a variant where any one of several ingredients suffices, memoizing a `false` found through a loop would be wrong.

### Pitfalls and edge cases

- Mark a recipe before recursing into its ingredients, or a loop recurses forever.
- Store the final verdict after the recursion, replacing the `ON_PATH` mark.

### Language notes

- Python: one dictionary holds `True`, `False` or the `ON_PATH` marker; the runner's raised recursion limit covers chains of 1000 recipes.
- TypeScript: a union type `"on path" | boolean` keeps the memo honest; `items.every(canPrepare)` stops at the first impossible ingredient.
- Java: a small `enum` with three states replaces nullable `Boolean` values.
- Kotlin: `verdict[item]?.let { return it == Verdict.PREPARABLE }` returns early for decided and in-progress recipes alike.
- Go: the memo is a `map[string]verdict` over a small `iota` type, and the zero value `undecided` stands for "not computed yet", so a missing key needs no comma-ok check. `canPrepare` is a closure declared with `var` first so it can call itself.
- Rust: the memo values are a three-variant enum, which makes "being explored" a state the compiler tracks instead of a magic string. The recursion is a method on a `Kitchen<'a>` struct that owns the lookup tables and borrows every name from the inputs; copying the stored `&'a [String]` out of `needs` before the loop lets the `all` closure borrow `self` mutably.
