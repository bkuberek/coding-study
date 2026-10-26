# Partition Labels: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n^2) | O(1) | first idea; a correctness baseline |
| last-occurrence | optimal | O(n) | O(1) | default answer |
| merge-intervals | optimal | O(n) | O(1) | you see it as the merge-intervals problem it is |

A piece that contains a letter must also contain that letter's last copy (and its first one). So the first piece has to stretch from index 0 at least to the last copy of `s[0]`, and further to the last copy of every letter inside that stretch. The greedy choice is to cut the moment the stretch stops growing: cutting as early as possible leaves the most room for later pieces.

## Approach: brute-force (Grow each part by searching for last occurrences)

### Intuition

Build the pieces one at a time. A piece starting at `start` must reach the last copy of `s[start]`; walking through the piece, every letter met may push the required end further. When the walk reaches the end without extending it, the piece is complete. Finding each last copy by searching the string is the slow part.

### Algorithm

1. Set `start = 0`.
2. While `start < n`: set `end` to the last index of `s[start]`; for each `position` from `start` to `end` (re-reading `end` as it grows), set `end = max(end, last index of s[position])`.
3. Record `end - start + 1`, set `start = end + 1`, and repeat.

### Correctness

The piece starting at `start` must contain the last copy of every letter it contains, so its end is at least every value the walk computes, and the walk stops at the smallest end with that property; that end is a valid cut because no letter inside has a copy beyond it, and the letters after it have no copy inside (otherwise their first copy would be inside and the walk would have extended). Cutting at the smallest valid end gives the most pieces by the exchange argument in the next approach.

### Complexity

- Time: O(n^2) — each position triggers a search for the last copy of its letter, O(n) each.
- Space: O(1) — a few indexes (the output is not counted).

### Trade-offs

Straightforward, so it is the oracle; it repeats the same "where is the last copy of this letter" search up to `n` times for at most 26 distinct letters. Library `lastIndexOf` searches are fast, but still linear.

### Pitfalls and edge cases

- The walk's upper bound grows while walking; a `for` loop over a fixed range would stop too early.
- A string with all letters distinct has `n` pieces of length 1.

### Language notes

- Python: `str.rfind` searches from the right in C.
- TypeScript, Java and Kotlin: `lastIndexOf` does the same; Java collects sizes in a `List<Integer>` and unboxes with `stream().mapToInt(...)`.

## Approach: last-occurrence (One pass with a table of last positions)

### Intuition

Precompute the last index of each letter once. Then one left-to-right walk can track the furthest last index among the letters of the current piece; when the walk's position equals it, the piece can close.

### Algorithm

1. Record `last[letter]` for every letter.
2. Walk the string with `start = 0` and `end = 0`: at each `index`, set `end = max(end, last[s[index]])`; if `index == end`, record `end - start + 1` and set `start = index + 1`.
3. Return the recorded sizes.

### Correctness

Invariant: within the current piece, `end` is the last index of any letter seen since `start`. When `index == end`, no letter of the piece appears after `index`, and no letter after `index` appears in the piece (each such letter's copies are all after `index`, or its last copy would have raised `end`), so cutting here is valid. Exchange argument: any valid partition must put every index up to this `end` in the same piece as `start` (each index was forced in by some letter's last copy), so this is the earliest possible cut; cutting at the earliest point never reduces the number of pieces that the rest of the string can form, because the rest is a suffix with fewer constraints. By induction the greedy partition has the most pieces, and it is the unique one with that many.

### Complexity

- Time: O(n) — two passes over the string.
- Space: O(1) — a table of 26 last positions.

### Trade-offs

The expected answer, and the cleanest greedy: one table, one pass. It is also the merge-intervals argument written without intervals.

### Pitfalls and edge cases

- Compute `end` before the comparison; the current letter may extend it.
- Do not reset `end` after a cut; the next letter's last index is always at least its own index, so `max` handles it.

### Language notes

- Python: a dict comprehension keeps the last index because later entries overwrite earlier ones.
- TypeScript: `charCodeAt(i) - 97` indexes a 26-slot array.
- Java and Kotlin: `charAt(i) - 'a'` (Java) and `letter - 'a'` (Kotlin) give the slot; both return an `int` array of sizes.

## Approach: merge-intervals (Merge the span of each letter)

### Intuition

Each letter covers the interval from its first copy to its last. A piece must contain whole intervals, and two overlapping intervals must share a piece. The pieces are therefore the merged intervals. Listing letters by their first occurrence lists the intervals sorted by start, so one merge pass suffices.

### Algorithm

1. Record the first and last index of each letter, keeping the letters in order of first occurrence.
2. Merge: for each interval, if it starts after the current merged end, close the current piece and start a new one at its start; extend the current end with its end.
3. Close the last piece and return the sizes.

### Correctness

Overlapping letter intervals must be in one piece, so every piece is a union of merged intervals; merged intervals are disjoint and together cover the string (every index belongs to its own letter's interval), so cutting between them is valid and gives the most pieces. The merge pass is correct because intervals arrive sorted by start, the standard condition for merging in one sweep.

### Complexity

- Time: O(n) — one pass to collect the at most 26 intervals, and a merge over them.
- Space: O(1) — at most 26 intervals.

### Trade-offs

Same speed as the last-occurrence pass; it makes the link to interval merging explicit, which helps when a variant changes the rules (for example, weights per letter).

### Pitfalls and edge cases

- The intervals are already sorted by start only because letters are visited in first-occurrence order; iterating the alphabet `a` to `z` would need a sort.
- Close the final piece after the loop.

### Language notes

- Python: dictionaries keep insertion order, so iterating `first` lists letters by first occurrence.
- TypeScript: a `Map` keeps insertion order too; each value is a `[first, last]` pair updated in place.
- Java: two 26-slot arrays plus a list of letters in first-occurrence order.
- Kotlin: a `LinkedHashMap` of `IntArray(2)` spans; `getOrPut` creates a span on the first copy, and destructuring `(first, last)` reads it.
