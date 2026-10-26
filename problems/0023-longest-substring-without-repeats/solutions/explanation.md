# Longest Substring Without Repeats: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n * min(n, a)) | O(min(n, a)) | as a correctness oracle; the alphabet is tiny |
| sliding-set | optimal | O(n) | O(min(n, a)) | default answer with any alphabet |
| last-index | optimal | O(n) | O(a) | the alphabet is small and fixed, as here |

Here `a` is the alphabet size: 95 printable ASCII characters. No substring without repeats can be longer than `a`, which is why `a` appears in the bounds.

## Approach: brute-force (Grow a window from every start)

### Intuition

Every candidate substring has a start. For a fixed start, extend to the right and stop at the first character already in the window: that run is the longest valid substring with this start, because any longer one contains the repeat too. Take the best over all starts.

### Algorithm

1. Set `best = 0`.
2. For each `start` from 0 to n - 1:
   1. Start an empty set `seen`.
   2. For `end` from `start` while `end < n` and `s[end]` is not in `seen`: add `s[end]` to `seen`.
   3. Set `best = max(best, len(seen))`.
3. Return `best`.

### Correctness

For a fixed start, the window `s[start .. end-1]` built by step 2 has no repeats, and `s[start .. end]` (if `end < n`) repeats `s[end]`, as does every longer substring with the same start. So the inner loop finds the longest valid substring for each start. Every substring has some start, so the maximum over starts is the answer. For an empty string the outer loop never runs and the answer is 0.

### Complexity

- Time: O(n * min(n, a)) — each start extends at most `min(n, a)` characters before a repeat must occur, by the pigeonhole principle.
- Space: O(min(n, a)) — the set holds the current run.

### Trade-offs

With an unbounded alphabet this is O(n^2), the usual "brute force" of interviews. With 95 possible characters it is at most about 95 times the linear scan, and on generated inputs that use the whole printable range it does roughly 50 steps per start. That makes it a fine oracle, and a good reminder that a bounded alphabet changes complexity arguments. It still restarts from scratch at every position and rescans what the previous start already saw.

### Pitfalls and edge cases

- The empty string returns 0, not 1.
- Spaces are characters: `banana split` has the answer `na split`, which includes the space.
- `aA` has length 2: case matters.

### Language notes

- Python: a fresh `set` per start; `range` loops with an early `break`.
- TypeScript: a fresh `Set<string>` per start; indexing `s[end]` yields one-character strings.
- Java: a fresh `boolean[128]` per start is cheaper than a `HashSet<Character>`, and the run length is `end - start`.
- Kotlin: `BooleanArray(128)` indexed by `Char.code`.

## Approach: sliding-set (Shrink the window one character at a time)

### Intuition

Keep one window `[left, right]` without repeats and slide it across `s`. When `s[right]` is already in the window, the window cannot be extended until that earlier copy has left it, so drop characters from the left, one at a time, until it is gone. Every character enters the window once and leaves it at most once.

### Algorithm

1. Start with an empty set `window`, `left = 0` and `best = 0`.
2. For each `right` with character `ch = s[right]`:
   1. While `ch` is in `window`, remove `s[left]` and increase `left`.
   2. Add `ch` and set `best = max(best, right - left + 1)`.
3. Return `best`.

### Correctness

Invariant: after step 2.2, `window` holds exactly the characters of `s[left .. right]`, all distinct, and `s[left .. right]` is the longest substring without repeats that ends at `right`. When `ch` is in the window, any substring ending at `right` that still contains its earlier copy is invalid, so the left edge must pass that copy; the loop removes exactly the characters up to and including it, and no further. Any valid substring ends at some `right`, so the maximum over all `right` is the answer.

### Complexity

- Time: O(n) — each character is added once and removed at most once, so the inner loop runs at most n times in total.
- Space: O(min(n, a)) — the window never holds more distinct characters than exist.

### Trade-offs

The canonical variable-size sliding window: grow on the right, shrink on the left while a constraint is violated. It works with any alphabet, including Unicode, since it only needs a hash set. It does up to 2n set operations; `last-index` halves that by jumping the left edge directly.

### Pitfalls and edge cases

- Shrink with `while`, not `if`: in `abcb`, reaching the second `b` requires removing both `a` and `b`.
- Remove `s[left]`, the character leaving the window, not `ch`.
- Update `best` after adding `ch`, so a window that just grew is measured.

### Language notes

- Python: `set.remove` and `set.add` are O(1) on average; `len(window)` equals `right - left + 1` by the invariant.
- TypeScript: `for (const ch of s)` iterates by code point, which equals iterating by index for the printable ASCII input here.
- Java: `HashSet<Character>` boxes characters; `Character.valueOf` caches all ASCII values, so no allocation happens per step.
- Kotlin: `HashSet<Char>` and the `in` operator; `for (ch in s)` iterates characters.

## Approach: last-index (Jump the window past the last occurrence)

### Intuition

Instead of removing characters one by one, remember where each character was last seen. When `s[right]` was last seen at position `p` inside the current window (`p >= left`), the new window must start at `p + 1`, so move `left` there in one step. If `p` lies before `left`, that copy has already left the window and changes nothing.

### Algorithm

1. Set `lastSeen[c] = -1` for every character `c`, `left = 0`, `best = 0`.
2. For each `right` with character `ch = s[right]`:
   1. If `lastSeen[ch] >= left`, set `left = lastSeen[ch] + 1`.
   2. Set `lastSeen[ch] = right` and `best = max(best, right - left + 1)`.
3. Return `best`.

### Correctness

Same invariant as `sliding-set`: `s[left .. right]` is the longest substring without repeats ending at `right`. If `ch` occurs in the window, its only occurrence there is the last one, at `lastSeen[ch]`, so the shortest move that removes it puts `left` at `lastSeen[ch] + 1`. If `lastSeen[ch] < left`, the window has no copy of `ch` and `left` stays. The check `>= left` keeps `left` from moving backwards, which would re-admit characters that caused earlier repeats.

### Complexity

- Time: O(n) — one pass with O(1) work per character.
- Space: O(a) — one slot per possible character (or a map with at most `min(n, a)` entries).

### Trade-offs

One pass, one array lookup per character, the fastest version. With a fixed small alphabet an array indexed by character code beats a hash map. For large or unknown alphabets use a map; then space is O(min(n, a)) like `sliding-set`. The `>= left` condition is the one subtle line, and interviewers like to probe it.

### Pitfalls and edge cases

- Only jump when the last occurrence is inside the window. `abba`: at the final `a`, its last position 0 is left of `left = 2`; jumping to 1 would move `left` backwards and report 3 instead of 2.
- Initialize positions to -1, not 0, or the first character would look like a repeat at position 0.
- `dvdf`: after the second `d`, `left` jumps to 1, giving `vdf` of length 3; restarting at the repeat position itself would give only 2.

### Language notes

- Python: a `dict` from character to position; `dict.get` returns `None` for unseen characters, which avoids a sentinel.
- TypeScript: `new Int32Array(128).fill(-1)` indexed by `charCodeAt`; typed arrays avoid both hashing and string allocation.
- Java: `int[128]` with `Arrays.fill(lastSeen, -1)`; a `char` indexes an array directly.
- Kotlin: `IntArray(128) { -1 }` and `Char.code`; `withIndex()` yields position and character together.
