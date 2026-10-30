# Permutations: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| used-flags | optimal | O(n * n!) | O(n * n!) | default answer; extends to duplicate values by skipping equal siblings |
| swap-in-place | optimal | O(n * n!) | O(n * n!) | you want no extra marker array and are free to reorder a working copy |

There are n! orderings of length n, so writing the answer alone costs n * n!. Both approaches reach that bound; they differ in how they remember which values are still free.

## Approach: used-flags (Fill slots left to right with a used flag per value)

### Intuition

Build one ordering slot by slot. Any value not used yet can go in the next slot, so try each of them in turn, recurse to fill the remaining slots, and then take the value back out so the next candidate can be tried. A boolean per value records which ones the current partial ordering already holds.

### Algorithm

1. Keep a shared `ordering`, a `used` array of n booleans and the result.
2. `fillNextSlot()`:
   1. If `ordering` has n values, append a copy to the result and return.
   2. For each index `i` with `used[i]` false: mark it used, append `nums[i]`, call `fillNextSlot()`, then pop the value and clear `used[i]`.
3. Call `fillNextSlot()` once and return the result.

### Correctness

Invariant: when `fillNextSlot` runs, `ordering` holds distinct values and `used[i]` is true exactly for the indexes in `ordering`. Each call extends the prefix by every unused value once, so by induction it emits every ordering that starts with the current prefix, each once: two siblings differ in the value at the current slot, so their subtrees cannot share an ordering. From the empty prefix this is every ordering of `nums` exactly once.

### Complexity

- Time: O(n * n!) — the recursion tree has n! leaves and fewer than e * n! nodes in total; each node scans n flags, and each leaf copies n values. Both are within a constant factor of n * n!.
- Space: O(n * n!) — the output holds n! lists of n values; the recursion depth, `ordering` and `used` add O(n).

### Trade-offs

The clearest backtracking skeleton: choose, recurse, undo. Scanning all n flags at every node costs a little more than the swap approach, which only iterates over the free suffix, but the asymptotics are the same. It is the version that adapts best to inputs with duplicates: sort, then skip a value equal to the previous one when that previous one is not in use.

### Pitfalls and edge cases

- Copy `ordering` when it is complete; appending the shared list stores n! references to one list.
- Clear `used[i]` after the recursive call, or later candidates are never tried.
- For one value the answer is a single ordering, not an empty list.

### Language notes

- Python: `[False] * len(nums)` is safe for immutable booleans (the list-of-lists trap does not apply).
- TypeScript: `new Array<boolean>(n).fill(false)`; `[...ordering]` copies.
- Java: `boolean[]` defaults to `false`; `ordering.remove(ordering.size() - 1)` uses the index overload because its argument is an `int`.
- Kotlin: `BooleanArray(n)` defaults to `false`; `ordering.toList()` makes the copy.
- Go: `make([]bool, len(nums))` starts all `false`. A recursive closure is declared first and assigned after so it can call itself, and `slices.Clone(ordering)` snapshots each finished ordering, because later appends reuse the same backing array.
- Rust: `vec![false; n]` starts all `false`. The recursion is a function that takes `used`, `ordering` and `result` as `&mut`, so the same buffers are shared down the whole recursion; `ordering.clone()` snapshots a finished ordering.

## Approach: swap-in-place (Swap each candidate into the next slot)

### Intuition

Use the array itself as both the partial ordering and the pool of free values: positions `0..slot-1` form the fixed prefix and positions `slot..n-1` hold exactly the values not placed yet. To choose a value for `slot`, swap it into that position, recurse on `slot + 1`, and swap it back.

### Algorithm

1. Copy `nums` into `values` so the input is not reordered.
2. `fixSlot(slot)`:
   1. If `slot == n`, append a copy of `values` to the result and return.
   2. For each `candidate` from `slot` to `n - 1`: swap `values[slot]` and `values[candidate]`, call `fixSlot(slot + 1)`, then swap them back.
3. Call `fixSlot(0)` and return the result.

### Correctness

Invariant: on entry to `fixSlot(slot)`, `values` is a rearrangement of `nums` whose suffix from `slot` holds exactly the values missing from the prefix, and the call leaves `values` exactly as it found it (every swap is undone). The loop puts each suffix value into position `slot` once, so the children explore prefixes that differ at `slot` and never repeat an ordering; by induction each call emits every ordering of its suffix after the fixed prefix. From `slot = 0` that is every ordering of `nums`.

### Complexity

- Time: O(n * n!) — n! leaves, each copying n values; the inner nodes iterate only over their free suffix, which adds the same order of work.
- Space: O(n * n!) — the output dominates; the working copy and the recursion depth add O(n).

### Trade-offs

No marker array and no membership test, so it does slightly less work per node. The orderings come out in a less regular sequence than with used flags (not lexicographic even for sorted input), which matters only if a problem asks for a specific order. Handling duplicates is more awkward: you need a per-slot set of values already tried.

### Pitfalls and edge cases

- Swap back after the recursive call; forgetting it corrupts the suffix and produces repeated orderings.
- Include `candidate == slot` in the loop: it is the "keep the current value here" choice.
- Work on a copy if the caller's array must stay unchanged.

### Language notes

- Python: tuple assignment swaps without a temporary.
- TypeScript: destructuring assignment `[a[i], a[j]] = [a[j], a[i]]` swaps; the spread copies the finished ordering.
- Java: `nums.clone()` copies the primitive array; each leaf boxes the values into an `ArrayList<Integer>`.
- Kotlin: `nums.copyOf()` copies the `IntArray`; `values.toList()` boxes a snapshot into a `List<Int>`.
- Go: `values[slot], values[candidate] = values[candidate], values[slot]` swaps in one statement, and `slices.Clone` copies the input first so the caller's slice is left in its order.
- Rust: `values.swap(slot, candidate)` swaps two elements of a slice in place, and `values.to_vec()` snapshots a finished ordering. The function owns `nums`, so it permutes that vector directly and needs no copy.
