# Debug: Binary Search Bounds: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| closed-interval | optimal | O(log n) | O(1) | default answer: one convention, `[lo, hi]` inclusive, used by every line |

## Approach: closed-interval (Closed-interval binary search)

### Intuition

The bug is a mix of two interval conventions. The initialization `hi = len(nums) - 1` describes a closed interval `[lo, hi]`: both ends are still candidates. The loop condition `lo < hi` and the update `hi = mid` belong to a half-open interval `[lo, hi)`, where `hi` is never a candidate. With the half-open condition, the loop stops while one candidate (`lo == hi`) is still unchecked. Since `mid = (lo + hi) // 2` is always strictly less than `hi` while `lo < hi`, index `len(nums) - 1` is never compared at all. That is exactly the ticket: the newest build (the last element) is never found, and neither is the only build of a one-element array.

The obvious one-character patch, `lo < hi` to `lo <= hi`, trades the wrong answer for a hang. Once `lo == hi` can enter the loop, `hi = mid` sets `hi` to the value it already has whenever `nums[mid] > target`. The interval stops shrinking, and any absent target smaller than some element loops forever. Both lines have to change together, because both follow from the same decision: what `hi` means.

### Debugging approach

1. **Reproduce.** The visible examples pass, so look for the failing input. Brute force a small space: every target position, plus a value below, between and above, for arrays of length 0 to 3. This takes seconds and shows that only "target at the last index" fails.
2. **Minimize.** The smallest failure is `nums = [7]`, `target = 7`: expected `0`, got `-1`.
3. **Trace.** For `[7]`, `lo = 0` and `hi = 0`, so `lo < hi` is false and the body never runs. One trace shows the loop condition skips the last candidate.
4. **Hypothesize, then test the hypothesis on the fix.** "The interval is closed, so the condition must be `<=`." Make that change alone and rerun: `[7]` with target 3 now times out. Trace it: `mid = 0`, `7 > 3`, `hi = mid = 0`, and nothing changes. The second line has the same root cause.
5. **Fix the invariant, not the symptom.** State what `[lo, hi]` means, then check every line against it: the initialization, the loop condition and both updates.

### Algorithm

1. Set `lo = 0` and `hi = len(nums) - 1`. The candidates are the closed interval `[lo, hi]`.
2. While `lo <= hi` (at least one candidate is left):
   1. Let `mid` be the midpoint of `lo` and `hi`.
   2. If `nums[mid] == target`, return `mid`.
   3. If `nums[mid] < target`, every index up to `mid` is too small: set `lo = mid + 1`.
   4. Otherwise every index from `mid` on is too large: set `hi = mid - 1`.
3. Return `-1`: no candidates are left.

### Correctness

Invariant: if `target` is in `nums`, its index lies in `[lo, hi]`. It holds at the start, since `[0, n - 1]` is the whole array. Each update removes only indices that cannot hold `target`: when `nums[mid] < target`, sorted order puts every index at or before `mid` below `target`, and symmetrically for `nums[mid] > target`. The loop runs while the interval is non-empty, so a present target is compared before the interval empties. The loop terminates because `mid` lies in `[lo, hi]` and each update moves `lo` above `mid` or `hi` below it, so the interval shrinks by at least one index per iteration. When it is empty, the invariant says `target` is absent, and `-1` is right.

### Complexity

- Time: O(log n) — each iteration halves the candidate interval, so there are at most about log2(n) + 1 iterations.
- Space: O(1) — three indices.

### Trade-offs

The half-open alternative is just as correct: `hi = len(nums)`, `while lo < hi`, and `hi = mid`. Applied to the buggy code it is a one-token fix (`len(nums) - 1` to `len(nums)`), because the loop condition and update were already half-open. The closed form shown here is the textbook "find an exact match" search. The half-open form is the better default for lower-bound and insertion-point searches, because `hi = len(nums)` is a valid answer there. Pick one per function and never mix them. A library call (`bisect_left` in Python, `Arrays.binarySearch` in Java) avoids the question entirely when it is allowed.

### Pitfalls and edge cases

- The general trap: an off-by-one in a binary search almost never shows on random tests. It shows at the boundaries: an empty array, one element, two elements, target first, target last, and targets below and above the whole range. Test those every time.
- Changing one bound without its partner moves the bug instead of fixing it. With `<=`, `hi = mid` loops forever; with `<`, `hi = mid - 1` skips candidates.
- Rounding must match the updates. With `hi = mid`, `mid` has to round down; with `lo = mid`, it has to round up. Get it backwards and a two-element interval never shrinks.
- In Java and Kotlin, `(lo + hi) / 2` overflows when `lo + hi` exceeds `2^31 - 1` (arrays of more than about a billion elements). Use `lo + (hi - lo) / 2` or `(lo + hi) >>> 1`.

### Prevention

- Write the invariant as a comment next to the initialization (`// candidates are [lo, hi]`), and review every bound against it.
- Keep a boundary test table (lengths 0, 1 and 2; first, last and missing on both sides) for every search you write. A property test that compares against a linear scan on random small arrays finds this bug in milliseconds.
- Put a hang guard on tests: an infinite loop must fail fast instead of blocking the suite. This repository's runner does this per case.
- Prefer the standard library's search when the problem allows it.

### Language notes

- Python: `(lo + hi) // 2` cannot overflow, since integers are arbitrary-precision. `bisect.bisect_left(nums, target)` gives the lower bound in C.
- TypeScript: `Math.floor((lo + hi) / 2)` is exact for any array length. `(lo + hi) >> 1` also works but is a 32-bit signed shift, so it breaks above `2^31 - 1`.
- Java: the fixed reference uses `(lo + hi) >>> 1`, the unsigned shift that stays correct even when `lo + hi` overflows. `Arrays.binarySearch` returns `-(insertion point) - 1` for a missing key, not `-1`.
- Kotlin: `ushr` is the unsigned shift. `nums.binarySearch(target)` follows the same negative-insertion-point convention as Java.
