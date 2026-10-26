# Median of Two Sorted Arrays: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| merge-and-sort | brute | O((m + n) log(m + n)) | O(m + n) | as a correctness oracle; never the interview answer |
| merge-to-middle | intermediate | O(m + n) | O(1) | a simple, safe answer when logarithmic time is not required |
| partition-search | optimal | O(log(min(m, n))) | O(1) | default answer for this problem |

`m` and `n` are the two lengths.

## Approach: merge-and-sort (Concatenate and sort)

### Intuition

The median is defined on the combined sorted values, so build them: concatenate the arrays, sort, and read the middle.

### Algorithm

1. `merged = sort(nums1 + nums2)`, and let `t` be its length and `middle = t / 2`.
2. If `t` is odd, return `merged[middle]`.
3. Otherwise return `(merged[middle - 1] + merged[middle]) / 2`.

### Correctness

Sorting the concatenation produces the combined values in non-decreasing order, and steps 2 and 3 are the definition of the median for odd and even `t`.

### Complexity

- Time: O((m + n) log(m + n)) — a general sort of the concatenation; it ignores that both halves are already sorted.
- Space: O(m + n) — the merged copy.

### Trade-offs

It is the shortest code and almost impossible to get wrong, which is all an oracle needs. It wastes both the existing order (a linear merge would do) and memory (only the middle values matter).

### Pitfalls and edge cases

- Divide by `2.0` (or use true division) for an even total: integer division would drop the `.5`.
- One array may be empty; concatenation handles it with no special case.

### Language notes

- TypeScript: `Array.prototype.sort` compares as strings by default; pass `(a, b) => a - b`.
- Java: `Arrays.copyOf` plus `System.arraycopy` builds the concatenation; `Arrays.sort` on `int[]` is a dual-pivot quicksort.
- Kotlin: `nums1 + nums2` concatenates two `IntArray`s into a new `IntArray`; `apply { sort() }` sorts it in place and returns it.

## Approach: merge-to-middle (Two-pointer merge up to the middle)

### Intuition

Both arrays are sorted, so the merged order can be produced one value at a time by always taking the smaller of the two front elements. The median only needs the values at positions `t / 2 - 1` and `t / 2`, so stop there and keep just the last two values seen.

### Algorithm

1. Let `t = m + n`, and set `i = j = 0`.
2. Repeat `t / 2 + 1` times: remember the previous value, then take the next merged value: `nums1[i]` if `nums2` is exhausted or `nums1[i] <= nums2[j]`, else `nums2[j]`, advancing that pointer.
3. If `t` is odd, return the last value taken; otherwise return the average of the last two.

### Correctness

The standard merge invariant: after `s` steps, the values taken are the `s` smallest of the combined collection, in order. After `t / 2 + 1` steps, the last value taken is the one at merged position `t / 2` and the one before it is at position `t / 2 - 1`; these are the middle value (odd `t`) or the two middle values (even `t`).

### Complexity

- Time: O(m + n) — about `(m + n) / 2` merge steps, each O(1).
- Space: O(1) — two pointers and two values; nothing is copied.

### Trade-offs

Linear time and constant memory, with code that is easy to reason about. It is a reasonable first answer, but the problem explicitly asks for logarithmic time, and interviewers expect the partition search.

### Pitfalls and edge cases

- The "take from `nums1`" test must check that `nums2` is exhausted first, and that `nums1` still has values; getting the order wrong reads past the end of an array.
- For `t = 1` the loop runs once and `previous` is never used.
- With `t` even, both remembered values matter; initializing them to 0 is safe because both are overwritten.

### Language notes

- Kotlin: `repeat(total / 2 + 1)` reads as "take that many merged values"; `nums1[i++]` returns the element and advances, as in Java.
- Java and Kotlin: `(previous + current) / 2.0` cannot overflow, since values are at most 10^6 in magnitude.

## Approach: partition-search (Binary search for the balanced partition)

### Intuition

Cut each array in two: the first `i` values of the shorter array and the first `j` values of the longer one form a lower half of fixed size `(m + n + 1) / 2`, so choosing `i` fixes `j`. The cut is the median cut exactly when every value in the lower half is at most every value in the upper half, which only needs two cross-checks: `short[i - 1] <= long[j]` and `long[j - 1] <= short[i]`. If the first check fails, `i` is too large; if the second fails, `i` is too small. That is a monotone decision, so `i` can be binary searched.

### Algorithm

1. Let `short` be the shorter array (length `s`) and `long` the other; `lowerSize = (m + n + 1) / 2`.
2. Binary search `i` in `[0, s]`; for each `i` let `j = lowerSize - i`.
3. Read the four border values `shortLeft = short[i - 1]`, `shortRight = short[i]`, `longLeft = long[j - 1]`, `longRight = long[j]`, using minus infinity for a missing left value and plus infinity for a missing right value.
4. If `shortLeft > longRight`, set `high = i - 1`; else if `longLeft > shortRight`, set `low = i + 1`; otherwise the cut is right:
   1. If `m + n` is odd, return `max(shortLeft, longLeft)`.
   2. Otherwise return `(max(shortLeft, longLeft) + min(shortRight, longRight)) / 2`.

### Correctness

For each `i`, `j` lies in `[0, len(long)]` because `short` is the shorter array, so the cut is well defined. The arrays are sorted, so the lower half is entirely at most the upper half exactly when both cross-checks hold. A correct cut exists: take the first `lowerSize` merged values and count how many came from `short`. If `shortLeft > longRight`, the lower half holds a value from `short` that is larger than an upper-half value from `long`, so every correct cut takes fewer values from `short`; symmetrically for the other check. The search therefore never discards the correct `i`. At the correct cut, the lower half holds the `lowerSize` smallest values, so its maximum is the middle value for odd totals, and the minimum of the upper half is the next value for even totals.

### Complexity

- Time: O(log(min(m, n))) — a binary search over the `min(m, n) + 1` possible cuts of the shorter array, with O(1) work per probe.
- Space: O(1) — a handful of indices and values.

### Trade-offs

This is the answer the problem is designed around. It is famously easy to get subtly wrong, so in an interview it pays to state the invariant ("lower half of size `(m + n + 1) / 2`, all of it at most the upper half") before coding, and to test the empty-array and all-in-one-array cuts. A more general alternative, "find the k-th smallest of two arrays" by discarding `k/2` values per step, runs in O(log(m + n)) and is easier to adapt to other ranks.

### Pitfalls and edge cases

- Search over the shorter array. Searching the longer one can make `j` negative or larger than the other array's length.
- Missing neighbors must behave like infinities. Java and Kotlin can use the `int` extremes only because the constraints keep values far from them; Python and TypeScript use real infinities.
- The `+ 1` in `lowerSize` puts the extra value in the lower half for odd totals, so the answer is the lower half's maximum. Mixing that convention with "the upper half's minimum" is a classic off-by-one.
- Adding two values near the `int` extremes would overflow; the Java and Kotlin references widen to `long` before adding, which is not strictly needed here but is the safe habit.

### Language notes

- Python: `math.inf` compares correctly with `int`s; `float(...)` makes the odd-total result a float, matching the declared `double` return.
- TypeScript: `Infinity` and `-Infinity` are ordinary numbers, so `Math.max` and `Math.min` handle missing neighbors; destructuring `[short, long]` swaps the arrays without a temporary.
- Java: the method calls itself once with the arguments swapped to make `nums1` the shorter array; `Integer.MIN_VALUE` and `Integer.MAX_VALUE` stand in for infinities.
- Kotlin: the same swap and `Int.MIN_VALUE` / `Int.MAX_VALUE` sentinels; `when` keeps the three outcomes of a probe in one expression.
