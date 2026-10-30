# Continuous Subarray Sum: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| every-pair | brute | O(n^2) | O(1) | short arrays, or as a correctness oracle |
| remainder-index | optimal | O(n) | O(min(n, k)) | default answer |

Both approaches rest on the same arithmetic fact: `a - b` is divisible by `k` exactly when `a` and `b` leave the same remainder modulo `k`.

## Approach: every-pair (Try every subarray of length two or more)

### Intuition

Fix a start, then extend the end one value at a time while keeping a running total. Every run of two or more values is tried once, and each extension costs one addition and one remainder.

### Algorithm

1. For every start `i`, set `total = nums[i]`.
2. For every end `j` from `i + 1` to `n - 1`: add `nums[j]` to `total`; if `total % k == 0`, return `true`.
3. Return `false` once every pair has been tried.

### Correctness

The loops enumerate every pair `i < j`, which is exactly the set of runs of length at least two, and `total` holds the sum of `nums[i..j]` when it is tested. The function returns `true` on the first qualifying run, and `false` only after every run has failed the test.

### Complexity

- Time: O(n^2) — up to n(n - 1)/2 runs, one addition and one remainder each.
- Space: O(1) — a running total and two indexes.

### Trade-offs

Direct and easy to trust, so it serves as the oracle. It wastes the structure of the problem: the remainders of the prefixes already decide every run, which the optimal approach exploits.

### Pitfalls and edge cases

- Start the inner loop at `i + 1`: a single value that is a multiple of `k` does not count.
- The running total can reach 10^14, so in Java and Kotlin it must be a `long`; an `int` overflows after three large values.
- A zero sum is a multiple of every `k`, so `[0, 0]` is always `true`.

### Language notes

- Go: `int` is 64 bits on a 64-bit platform, so a running total of up to 10^14 needs no widening. `nums[start+1:]` is a view of the same array, so the inner loop starts at the second element without a copy.
- Rust: a sum can reach 10^14, so the total and the modulus are `i64`, widened with `i64::from`; an `i32` total would panic, because the build checks overflow. `&nums[start + 1..]` is empty for the last start, so the inner loop simply does not run.

## Approach: remainder-index (First index of every prefix remainder)

### Intuition

Let `prefix[t]` be the sum of the first `t` values. The run `nums[i..j]` adds up to `prefix[j + 1] - prefix[i]`, which is a multiple of `k` exactly when both prefixes have the same remainder modulo `k`. So walk the array keeping the remainder of the running sum and, for each remainder, the earliest position where it appeared. Meeting a remainder again at least two positions after its first appearance means a run of length at least two. Keeping the earliest position is enough, because it gives the longest run for that remainder.

### Algorithm

1. Start a map `first_index = {0: -1}` (the empty prefix ends before position 0) and `remainder = 0`.
2. For each position `p` with value `v`:
   1. `remainder = (remainder + v) % k`.
   2. If `remainder` is not in the map, record `first_index[remainder] = p`.
   3. Otherwise, if `p - first_index[remainder] >= 2`, return `true`.
3. Return `false`.

### Correctness

After step 2.1, `remainder` equals `prefix[p + 1] mod k`, because `(a mod k + v) mod k = (a + v) mod k`. If the function returns `true` at `p`, the earlier position `e = first_index[remainder]` has the same prefix remainder, so `nums[e + 1..p]` is a run of length `p - e >= 2` whose sum is divisible by `k`. Conversely, if some run `nums[i..j]` with `i < j` qualifies, then `prefix[i]` and `prefix[j + 1]` share a remainder; when the walk reaches `j`, the map holds a first position `e <= i - 1` for it, so `j - e >= j - i + 1 >= 2` and the function returns `true` at `j` at the latest. Recording only first positions never hides an answer, since an earlier position only makes the distance larger.

### Complexity

- Time: O(n) — one pass with O(1) average map operations per value.
- Space: O(min(n, k)) — the map holds at most one entry per distinct remainder, and there are at most `k` remainders and `n + 1` prefixes.

### Trade-offs

Linear and the expected answer. It needs a map, where the brute force needs nothing, and the reasoning about "first position" and "length at least two" is where most bugs hide. When `k` is small, an array of size `k` can replace the map.

### Pitfalls and edge cases

- Seed the map with remainder 0 at position -1, otherwise runs that start at position 0 are missed (for example `[2, 4]` with `k = 6`).
- Never overwrite a remainder's position when it reappears too soon. With `[3, 0, 3]` and `k = 3`, the remainder 0 reappears at positions 0, 1 and 2, each time only one position after the previous one; keeping -1 finds the run `[3, 0]` at position 1, while overwriting returns `false`.
- `remainder + value` can exceed 2^31 - 1 (a remainder just below `k` plus a value of 10^9), so Java and Kotlin add in 64 bits before reducing.

### Language notes

- Python: `dict.setdefault(remainder, position)` records the first position and returns whichever position is stored, in one lookup; integers never overflow.
- TypeScript: numbers are doubles, and every intermediate value stays below 2^53, so `%` is exact. `Map.get` returns `undefined` for a missing remainder.
- Java: `putIfAbsent` returns the stored position or `null`; the remainder update casts to `long` first: `(int) (((long) remainder + nums[p]) % k)`.
- Kotlin: the same `putIfAbsent` on a `HashMap<Int, Int>` returns `Int?`; `remainder.toLong() + value` keeps the sum in 64 bits.
- Go: the comma-ok lookup `earlier, seen := firstIndex[remainder]` plays the part of Python's `setdefault`: when the remainder is new the position is stored and the loop continues, otherwise the stored position is compared. `remainder + value` stays below 2^31 + 10^9, which Go's 64-bit `int` holds.
- Rust: `*first_index.entry(remainder).or_insert(position)` is the `setdefault` equivalent: it inserts only when the key is new and returns the stored value either way. Because `k` can be up to `i32::MAX`, `remainder + value` can pass `i32::MAX`, so remainders, positions and the modulus are all `i64`.
