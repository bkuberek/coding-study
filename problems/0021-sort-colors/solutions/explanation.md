# Sort Colors: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| counting | intermediate | O(n) | O(1) | values carry no extra data, or as a correctness oracle |
| dutch-flag | optimal | O(n) | O(1) | default answer; the follow-up asks for one pass |

Both approaches are linear with constant memory. The difference is one pass versus two, and whether elements are moved (swapped) or regenerated (overwritten).

## Approach: counting (Count each color then overwrite)

### Intuition

Three possible values make a counting sort trivial: count how many `0`s, `1`s and `2`s there are, then write that many of each, in order, over the array.

### Algorithm

1. Count the occurrences `c0`, `c1`, `c2` of each color in one pass.
2. Write `0` into positions `0 .. c0-1`, `1` into `c0 .. c0+c1-1` and `2` into the rest.

### Correctness

The counts capture the multiset of colors exactly, and step 2 writes the same multiset in non-decreasing order. Because the values are just colors with no identity, rewriting them is indistinguishable from moving them.

### Complexity

- Time: O(n) — one counting pass and one writing pass.
- Space: O(1) — three counters, independent of n.

### Trade-offs

Simplest correct in-place solution, hence the oracle. It reads the array twice and writes every position once. It relies on the values being plain colors: if each token carried data (a record with a color key), overwriting would lose that data, while the swap-based Dutch flag still works. It generalizes trivially to `k` colors with `k` counters.

### Pitfalls and edge cases

- A missing color gives a zero count; the fill ranges must still be correct, for example an empty `0` block when there are no `0`s.
- Mutate `nums` itself. In Python, `nums = [0] * c0 + ...` rebinds the name and leaves the caller's list unchanged.

### Language notes

- Python: indexing `counts[color]` with the color itself keeps the counting loop short; the write-back uses explicit index assignment to stay in place.
- TypeScript: `Array.prototype.fill(value, start, end)` writes each block; the end is exclusive.
- Java: `Arrays.fill(nums, from, to, value)` writes each block; `to` is exclusive.
- Kotlin: `IntArray.fill(element, fromIndex, toIndex)` mirrors the Java call.
- Go: `var counts [3]int` is a zeroed array indexed by the color, and `for range count` (Go 1.22) repeats a block without a loop variable. The function edits the caller's slice in place.
- Rust: the colors arrive as `i32`, so the count array is indexed with `color as usize`, and `nums[index..index + count].fill(color as i32)` writes each block in one call. The result goes back through the `&mut Vec<i32>` parameter.

## Approach: dutch-flag (One pass with three regions)

### Intuition

Partition the array into four regions with three indices: `[0, low)` holds `0`s, `[low, mid)` holds `1`s, `[mid, high]` is still unknown, and `(high, n)` holds `2`s. Look at `nums[mid]`, the first unknown value. A `0` is swapped to the end of the `0` block, a `1` simply joins the `1` block, and a `2` is swapped to the front of the `2` block. Each step shrinks the unknown region by one.

### Algorithm

1. Set `low = 0`, `mid = 0`, `high = n - 1`.
2. While `mid <= high`:
   - If `nums[mid] == 0`: swap `nums[low]` and `nums[mid]`, then increase both `low` and `mid`.
   - If `nums[mid] == 1`: increase `mid`.
   - If `nums[mid] == 2`: swap `nums[mid]` and `nums[high]`, then decrease `high` only.

### Correctness

The four-region invariant holds initially (all regions but the unknown one are empty). In the `0` case, `nums[low]` is either the first `1` (when `low < mid`) or `nums[mid]` itself (when `low == mid`); after the swap, position `low` holds a `0` and position `mid` holds a `1`, so advancing both keeps the invariant. In the `1` case, the `1` block grows by one. In the `2` case, the value swapped in from `high` has not been examined yet, so `mid` must stay put; decreasing `high` adds the `2` to the back block. The unknown region shrinks every iteration and the loop ends when it is empty, leaving `0`s, `1`s and `2`s in order. Swaps only permute elements, so the multiset is unchanged.

### Complexity

- Time: O(n) — each iteration increases `mid` or decreases `high`, so there are at most n iterations.
- Space: O(1) — three indices.

### Trade-offs

One pass, swaps instead of overwrites, so it also sorts records by a three-valued key. It is the classic three-way partition used by quicksort variants that handle many equal keys. It is easier to get wrong than counting: the asymmetric pointer moves after the two swaps are the whole point. For `k > 3` colors it does not generalize directly; counting, or repeated partitioning, is used instead.

### Pitfalls and edge cases

- Do not advance `mid` after swapping with `high`: the value that arrives from the back is unknown. On `[1, 2, 0]`, the `2` swaps with the `0`; advancing `mid` past that `0` leaves `[1, 0, 2]`.
- The loop condition is `mid <= high`, not `mid < high`; the element at `high` is still unknown until `mid` passes it.
- With `high` starting at `n - 1`, an array of length 1 runs exactly one iteration.

### Language notes

- Python: tuple assignment swaps two list elements without a temporary.
- TypeScript: a small `swap` helper with a temporary is faster than destructuring, which allocates a two-element array per swap.
- Java: `swap(nums, low++, mid++)` passes the old index values and advances both, which keeps the three branches one line each.
- Kotlin: a private `IntArray.swap` extension uses the `also` idiom; `when (nums[mid])` with constant branches reads like the case analysis above.
- Go: `switch nums[mid]` with constant cases reads like the case analysis above, and the tuple assignment swaps two slots without a temporary.
- Rust: `match nums[mid]` on the three colors, with `Vec::swap` exchanging two slots. `high` is stored one past the unsorted region and decremented before a swap, so an empty vector cannot underflow `usize`.
