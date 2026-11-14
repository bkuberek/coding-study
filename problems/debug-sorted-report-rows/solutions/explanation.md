# Debug: Sorted Report Rows: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| sorted-indices | optimal | O(n log n) | O(n) | default answer: sort positions, so each total stays beside its region and the input stays as it was |

## Approach: sorted-indices (Sort indices with a numeric comparator)

### Intuition

Three bugs share one line and its neighbor.

1. **`.sort()` compares as strings.** With no compare function, JavaScript turns every item into a string and compares UTF-16 code units, so `[1000, 90, 5].sort()` is `[1000, 5, 90]`. It looks right for totals with the same number of digits, which is why the old reports were fine.
2. **`.sort()` sorts in place and returns the same array.** `ranked` and `totalsCents` are one array, so by the time `indexOf` runs, the positions no longer line up with `regions`. Each total ends up beside whichever region sat at that rank in the input.
3. **`indexOf` finds the first match.** Even after you fix the first two with a copy, two regions with equal totals both resolve to the first one.

### Say it out loud

"`Array.prototype.sort` sorts in place and, without a comparator, compares as strings. So I need a numeric comparator, and I don't sort the caller's array. Here the values aren't enough on their own, because two rows can have the same total, so I sort positions and look everything up by position."

### Debugging approach

1. **Reproduce small.** `topRegions(["a", "b"], [5, 1000], 2)` already shows the problem: the rows are wrong in both the order and the pairing.
2. **Separate the symptoms.** The report has two complaints: numbers beside the wrong names, and 1000 sorting low. Two complaints may mean two bugs.
3. **Log the input after the call.** `console.log(totalsCents)` after the sort shows it reordered. A function that was handed an array has changed it.
4. **Check the half-fixes.** A numeric comparator alone leaves the in-place sort (`h1`). A copy alone leaves the string compare (`h2`). Both, with `indexOf`, leave the equal totals (`h4`), and an index sort with no tie-break leaves the name order (`h5`).

### Algorithm

1. Build the array of positions `0..n-1`.
2. Sort it by total descending, then by region name ascending.
3. Take the first `limit` positions and format each row from the two input arrays.

### Correctness

The comparator is a total order: totals are compared by value, and names are distinct, so no two positions compare equal, and the sorted order is unique. Each position still refers to one region and its total, because neither input array moves, so a row can't pair a region with another region's total. `slice` handles a `limit` of zero and a `limit` above the length.

### Complexity

- Time: O(n log n) — one sort of `n` positions; each comparison is O(1) for totals and O(name length) for the rare tie, and names are short.
- Space: O(n) — the array of positions.

### Trade-offs

Building `{ region, total }` objects and sorting those reads a little better and allocates a little more. `toSorted` (Node 20 and later) makes the copy explicit: `totalsCents.toSorted((a, b) => b - a)` is the right habit for sorting values, though it doesn't solve the pairing. A partial selection of the top `limit` is O(n log limit), which doesn't matter at these sizes.

### Pitfalls and edge cases

- The general trap: `.sort()` with no comparator is a string sort, on numbers too. Always pass a comparator for numbers.
- `.sort()` and `.reverse()` return the same array they changed, so `const sorted = input.sort()` looks like a copy and isn't. The same goes for `splice` and `fill`. `toSorted`, `toReversed` and `toSpliced` are the versions that copy.
- `(a, b) => a < b` is a common wrong comparator. It returns a boolean, which counts as 0 or 1, never negative, so the sort gets a contradictory answer (`h11`).
- `.reverse()` after an ascending sort also reverses ties: fine for values, wrong for a tie-break you meant to keep.
- `b - a` is safe here, since totals stay far below `2^53`. In a language with fixed-width integers, subtracting can overflow.
- `localeCompare` depends on the locale; `<` compares code units, the same everywhere. The statement asks for `<`.

### Prevention

- The lint rule `require-array-sort-compare` flags a `.sort()` with no comparator.
- Mark inputs `readonly number[]`, and the compiler rejects `.sort()` on them, leaving `toSorted`.
- Test with totals of different digit counts and with equal totals; a single example with same-length numbers hides all three bugs.

### Language notes

TypeScript type-checks this bug without a complaint: `totalsCents.sort()` on a `number[]` returns `number[]`, whatever it compared by. The types say nothing about the order, or about whether an array was changed.
