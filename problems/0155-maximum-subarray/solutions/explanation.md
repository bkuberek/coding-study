# Maximum Subarray: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n^2) | O(1) | n is small, or as a correctness baseline |
| divide-and-conquer | intermediate | O(n log n) | O(log n) | the follow-up asks for it, or many range queries need a segment tree |
| kadane | optimal | O(n) | O(1) | default answer |

Kadane's algorithm sits on the border of greedy and dynamic programming. As a DP, the state is `best[i]`, the best sum of a subarray that ends at index `i`, with `best[i] = max(nums[i], best[i - 1] + nums[i])`; the table can be rolled into one variable. As a greedy, the rule is "drop the running sum as soon as it is negative", justified by an exchange argument.

## Approach: brute-force (Extend a sum from every start)

### Intuition

Fix each start and extend the subarray one element at a time, updating its sum in O(1). Every subarray is visited once, so the best one is found in quadratic time.

### Algorithm

1. Set `best = nums[0]`.
2. For each `start`, set `total = 0`; for each `end >= start`, add `nums[end]` and update `best`.
3. Return `best`.

### Correctness

Each pair `start <= end` is visited once, with `total` equal to the sum of `nums[start..end]` at that moment. Starting `best` at `nums[0]` (a real subarray) rather than 0 keeps all-negative arrays correct.

### Complexity

- Time: O(n^2) — n(n + 1) / 2 additions.
- Space: O(1) — two running values.

### Trade-offs

Clear and short, so it is the oracle; far too slow for 10^5 elements.

### Pitfalls and edge cases

- Initializing `best` to 0 returns 0 for `[-3, -1, -2]`, but the empty subarray is not allowed.

### Language notes

- Sums stay within 10^5 * 10^4 = 10^9 in absolute value, inside 32-bit range, in every language.

## Approach: divide-and-conquer (Best of the left half, the right half and the crossing sum)

### Intuition

Split the array in the middle. The best subarray lies entirely in the left half, entirely in the right half, or crosses the middle. The first two are smaller instances of the same problem. A crossing subarray is a suffix of the left half joined to a prefix of the right half, and the best one combines the best suffix with the best prefix, each found in one linear scan.

### Algorithm

1. `bestIn(low, high)`: if `low == high`, return `nums[low]`.
2. Let `middle` be the midpoint. Scan left from `middle` for the best suffix sum, and right from `middle + 1` for the best prefix sum.
3. Return the maximum of `bestIn(low, middle)`, `bestIn(middle + 1, high)` and `bestSuffix + bestPrefix`.

### Correctness

Every subarray of `low..high` falls into exactly one of the three cases. The crossing case contains `nums[middle]` and `nums[middle + 1]`, and its two sides can be chosen independently, so its maximum is the sum of the independent maxima. The halves are correct by induction on the length.

### Complexity

- Time: O(n log n) — each level of recursion scans every element once, and there are about log n levels.
- Space: O(log n) — the recursion depth.

### Trade-offs

Slower than Kadane and longer to write, but it is the version that generalizes: storing for each segment its total, best prefix, best suffix and best subarray gives a segment tree that answers "maximum subarray in range `[l, r]`" with updates in O(log n).

### Pitfalls and edge cases

- Both crossing scans must include their first element (`nums[middle]` and `nums[middle + 1]`); otherwise a crossing subarray could be empty on one side and double-count a half.
- The base case is a single element, so every recursive range is non-empty.

### Language notes

- Python: a nested function over index bounds avoids slicing, which would copy subarrays at every level.
- TypeScript and Kotlin: a closure over `nums`; Java passes the array to a private method.
- Java and Kotlin: `>>>` and `ushr` compute the midpoint without overflow by habit.
- Go: a closure declared with `var bestIn func(low, high int) int`; the built-in `max` takes three arguments, so the three candidates fit in one call.
- Rust: a private function over `&[i32]`; `nums[low..=middle].iter().rev()` walks the left half outwards from the middle, and `Ord::max` takes two arguments, so the three candidates chain. Slicing borrows, so no subarray is copied.

## Approach: kadane (Kadane's running best sum)

### Intuition

Let `endingHere` be the best sum of a subarray that ends at the current index. The best subarray ending at `i` either is `nums[i]` alone or extends the best one ending at `i - 1`; extending only helps when that previous best is positive. Keep the largest `endingHere` seen.

### Algorithm

1. Set `endingHere = best = nums[0]`.
2. For each later index: `endingHere = max(nums[i], endingHere + nums[i])`; `best = max(best, endingHere)`.
3. Return `best`.

### Correctness

DP view: by induction, `endingHere` equals `best[i]` as defined in the overview, because every subarray ending at `i` is `[nums[i]]` or a subarray ending at `i - 1` followed by `nums[i]`, and the best of the second kind uses the best subarray ending at `i - 1`. Every subarray ends somewhere, so the maximum over `i` is the answer. Greedy view (exchange argument): if a candidate subarray starts with a prefix whose sum is negative, removing that prefix gives a strictly better subarray, so an optimal subarray never begins with a negative running sum; restarting when `endingHere + nums[i] < nums[i]` (that is, when `endingHere < 0`) discards exactly such prefixes.

### Complexity

- Time: O(n) — one pass with constant work per element.
- Space: O(1) — two integers.

### Trade-offs

The expected answer: one pass, two variables, and a proof that works both as a recurrence and as an exchange argument. It does not support range queries or updates; the divide-and-conquer structure does.

### Pitfalls and edge cases

- Start from `nums[0]`, not 0, so an all-negative array returns its largest element.
- `max(nums[i], endingHere + nums[i])` handles the restart without a separate `if`.
- To report the subarray itself, remember where the current run started whenever it restarts.

### Language notes

- All four languages use the same two-variable loop with `max` / `Math.max` / `maxOf`.
- Go and Rust use it as well, over `nums[1:]` and `&nums[1..]`, which borrow the tail instead of copying it.
