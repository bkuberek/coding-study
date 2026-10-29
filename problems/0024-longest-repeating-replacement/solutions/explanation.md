# Longest Repeating Replacement: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n^2) | O(1) | n is small, or as a correctness oracle |
| per-letter | intermediate | O(a * n) | O(a) | you want a simple linear window with an easy invariant |
| sliding-window | optimal | O(n) | O(1) | default answer |

Here `a` is the alphabet size, 26. All approaches rely on one test: a window can be made uniform with at most `k` replacements exactly when `length - maxCount <= k`, where `maxCount` is the count of its most common letter. Replacing every other letter with that one is optimal for the window.

## Approach: brute-force (Extend a window from every start)

### Intuition

Fix the start of the window and extend it to the right, keeping letter counts and the largest count. As soon as `length - maxCount` exceeds `k`, no longer window with this start can work either, so stop and move to the next start.

### Algorithm

1. Set `best = 0`.
2. For each `start`:
   1. Reset 26 counts and `most = 0`.
   2. For each `end` from `start`: increase the count of `s[end]`, update `most`, and if `end - start + 1 - most > k` stop; otherwise set `best = max(best, end - start + 1)`.
3. Return `best`.

### Correctness

For a fixed start, `length - maxCount` never decreases as the window grows: the length grows by 1 and `maxCount` by at most 1. So once a window from this start fails, all longer ones fail too, and the loop has already measured the longest valid one. Every window has a start, so the maximum over starts is the answer.

### Complexity

- Time: O(n^2) — each start can extend up to n characters. With the generator's budgets (n/16 to n/8) valid windows are long, so the work stays quadratic.
- Space: O(1) — 26 counters.

### Trade-offs

Straightforward and safe, so it is the oracle. It rebuilds the counts from scratch at every start, which is exactly what a sliding window avoids. At n = 10^4 it takes about 10^7 steps, a couple of seconds in Python.

### Pitfalls and edge cases

- Stop at the first failing window: continuing is correct but wasteful, and it does not change the answer.
- `k = 0` reduces to the longest run of one letter.
- `k >= n` always gives n.

### Language notes

- Python: `ord(ch) - 65` maps `A` to 0; an explicit comparison instead of `max` keeps the inner loop cheaper.
- TypeScript: `Int32Array(26)` per start; `++counts[letter]` returns the new count.
- Java: `int[26]` and `s.charAt(end) - 'A'`; prefix increment inside `Math.max` is idiomatic here.
- Kotlin: subtracting `'A'` from a `Char` gives an `Int` index.
- Go: `var counts [26]int` is a zeroed array per start, and `s[end] - 'A'` is a `byte` that indexes it directly; the builtin `max` replaces the manual comparisons.
- Rust: `[0usize; 26]` is rebuilt per start. `k` arrives as `i32` and is converted once to `usize`, so the comparison `end - start + 1 - most > k` stays in one type; `end - start + 1 - most` cannot underflow because `most` never exceeds the window length.

## Approach: per-letter (One window per letter that is kept)

### Intuition

If you knew which letter the final run consists of, the problem would be Max Consecutive Ones With K Flips: find the longest window with at most `k` characters different from that letter. There are only 26 letters, so try each one with a standard shrinking window and keep the best.

### Algorithm

1. For each letter `target` that occurs in `s`:
   1. Slide a window `[left, right]`, counting `others`, the characters different from `target`.
   2. When `others > k`, move `left` right until it is at most `k` again.
   3. Track the largest window length.
2. Return the best length over all letters.

### Correctness

For a fixed target, the window invariant `others <= k` holds after every shrink, and for each `right` the window is the longest one ending there with at most `k` non-target characters, by the usual sliding-window argument: moving `left` further left would add non-target characters back. The answer's run consists of some letter `c`; trying `c` as the target finds a window at least that long. Letters absent from `s` cannot do better than a letter present, so skipping them is safe.

### Complexity

- Time: O(a * n) — one linear sliding window per letter present, at most 26.
- Space: O(a) — the set of letters present; the window itself needs two counters.

### Trade-offs

Linear, with an invariant that is easy to state and prove, and it reuses a pattern you may already know. It reads `s` up to 26 times, so the single-window solution is up to 26 times faster. It is a good fallback if the stale-maximum argument of the optimal solution feels shaky in an interview.

### Pitfalls and edge cases

- Shrink with `while`, not `if`: dropping a target letter from the left does not reduce `others`, so several steps may be needed. With target `A` and `k = 0`, the window `AAB` must drop all three characters.
- Counting `others` must use the same comparison when entering and leaving the window.

### Language notes

- Python: `set(s)` gives the letters present; iteration order does not matter because only the maximum is kept.
- TypeScript: `new Set(s)` iterates the distinct characters of the string.
- Java: `s.indexOf(target) < 0` skips letters that do not occur.
- Kotlin: `s.toSet()` gives the distinct characters.
- Go: `strings.IndexByte(s, target) < 0` skips a letter that never occurs, the counterpart of Java's `s.indexOf(target) < 0`; looping over the `byte` range `'A'` to `'Z'` replaces Python's `set(s)`.
- Rust: `b'A'..=b'Z'` iterates the letters and `bytes.contains(&target)` skips the absent ones. The window length is written `right + 1 - left`, not `right - left + 1`: the shrink loop can step `left` one past `right` (an empty window), and `right - left` would underflow `usize` first.

## Approach: sliding-window (One window with a never-decreasing top count)

### Intuition

Use one window with 26 counts and `most`, the largest count seen in any window so far. Only windows longer than the best one matter, and a window of length `L` can beat the best only if its most common letter appears at least `L - k` times. So the window never needs to shrink: when it becomes invalid, slide it one step to the right (drop one character on the left as the new one enters). And `most` never needs to decrease: a stale, too-large `most` can only make the window look valid when its length equals a length that was already achieved, which never inflates the answer.

### Algorithm

1. Set all 26 counts to 0, `most = 0`, `left = 0`, `best = 0`.
2. For each `right`:
   1. Increase the count of `s[right]` and set `most = max(most, that count)`.
   2. If `right - left + 1 - most > k`, decrease the count of `s[left]` and increase `left`.
   3. Set `best = max(best, right - left + 1)`.
3. Return `best`.

### Correctness

The window length never decreases: each iteration adds one character and removes at most one. Let `L` be the length before step `right`, and assume by induction that `L` is the best answer within `s[0 .. right-1]`. After adding `s[right]`, the window is the last `L + 1` characters. Two facts hold:

1. `most` is at least the true top count `m` of the current window. The counts are exact, and whenever a count reached its current value, `most` was raised to at least that value.
2. `most` is the top count of some earlier window of length at most `L + 1`, since the window was never longer than that.

If a valid window of length `L + 1` ends at `right`, it is the current window, and by fact 1 the test `L + 1 - most <= k` passes, so the window grows. If no valid window of length `L + 1` exists in `s[0 .. right]`, the test must fail: otherwise `most >= L + 1 - k`, and by fact 2 some window of length at most `L + 1` holds one letter `most` times; widening it to length exactly `L + 1` inside `s[0 .. right]` keeps those letters, so it needs at most `L + 1 - most <= k` replacements, a contradiction. A new best window must end at `right`, so the window grows exactly when the answer grows, and its length is always the best answer so far.

### Complexity

- Time: O(n) — one pass with O(1) work per character.
- Space: O(1) — 26 counters and three integers.

### Trade-offs

Fastest and shortest, and the solution interviewers look for. Its correctness argument (a stale `most` is harmless) is subtle; be ready to explain it, or present `per-letter` first. A variant that recomputes the exact maximum over the 26 counts after each shrink is easier to justify and costs O(a * n).

### Pitfalls and edge cases

- Slide with `if`, not `while`. The argument above relies on the window keeping its length; shrinking it further gains nothing and, combined with a stale `most`, makes the window's state hard to reason about.
- Do not decrease `most` when a character leaves the window.
- Update `best` after the slide; it equals the final window length anyway, so returning `n - left` is an equivalent shortcut.

### Language notes

- Python: a 26-element list indexed by `ord(ch) - 65` is faster than a `Counter`.
- TypeScript: `Int32Array(26)` and `charCodeAt` avoid string allocation per character.
- Java: `int[26]` indexed by `s.charAt(i) - 'A'`.
- Kotlin: `IntArray(26)` indexed by `s[i] - 'A'`; `++counts[...]` returns the updated count.
- Go: one window, one `[26]int` array and a `most` that never decreases; the window shrinks by at most one position per step, so the `if` replaces an inner loop.
- Rust: the same `[usize; 26]` array and a never-decreasing `most`. Every counter is `usize`, so the subtraction `right - left + 1 - most` relies on `most` being at most the window length, which holds because `most` counts letters inside a window that is never shorter than it.
