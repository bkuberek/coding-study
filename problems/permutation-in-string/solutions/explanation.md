# Permutation in String: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| sort-windows | brute | O(n * m log m) | O(m) | as a correctness oracle |
| window-counts | intermediate | O(a * n + m) | O(a) | simplest linear version; a is small |
| match-count | optimal | O(n + m) | O(a) | default answer, independent of the alphabet size |

Here `n` is the length of `text`, `m` the length of `pattern` and `a = 26` the alphabet size. Every approach tests windows of length `m`: a rearrangement of `pattern` must have exactly `m` letters.

## Approach: sort-windows (Sort every window and compare)

### Intuition

Two strings are rearrangements of each other exactly when sorting them gives the same string. Sort the pattern once, then sort each window of length `m` of the text and compare.

### Algorithm

1. Let `target` be the sorted letters of `pattern`.
2. For each start from 0 to `n - m`: sort the letters of `text[start .. start+m-1]`; if they equal `target`, return `true`.
3. Return `false` (this also covers `m > n`, where the loop does not run).

### Correctness

Sorting maps all rearrangements of a multiset of letters to the same sequence, and different multisets to different sequences. So a window matches `target` exactly when it is a rearrangement of `pattern`. Every substring of length `m` is a window for some start, so the search is exhaustive.

### Complexity

- Time: O(n * m log m) — up to `n - m + 1` windows, each copied and sorted in O(m log m). The generator ties `m` to n/8 to n/4, so this grows like n^2 log n.
- Space: O(m) — the sorted window.

### Trade-offs

Obviously correct and short, hence the oracle. It throws away all work between neighboring windows, which share `m - 1` letters, and pays a sort per window. At n = 10^4 with `m` around 2000 that is on the order of 10^8 steps.

### Pitfalls and edge cases

- If the pattern is longer than the text, no window exists: the answer is `false`, not an error.
- Compare sorted letters, not sets: `aab` and `abb` have the same letters but different counts.
- Loop while `start + m <= n`; an off-by-one misses a match at the very end of the text.

### Language notes

- Python: `sorted(text[start:start + m])` returns a list of one-character strings; comparing lists is element-wise in C.
- TypeScript: sorting a `Uint8Array` of char codes is numeric and much faster than `split("").sort()`, which compares strings.
- Java: `toCharArray`, `Arrays.sort` (a primitive sort) and `Arrays.equals`.
- Kotlin: `toCharArray().apply { sort() }` sorts in place and returns the array; `contentEquals` compares contents, while `==` on arrays compares references.
- Go: strings are immutable, so each window is copied into a `[]byte` with `[]byte(text[start:start+width])` and sorted with `slices.Sort`; `slices.Equal` compares it with the sorted pattern.
- Rust: `bytes.windows(width)` yields every window as a borrowed subslice, `to_vec` copies it so it can be sorted, and `==` on two `Vec<u8>` compares contents. `windows` yields nothing when the text is shorter than the pattern (it panics for a width of 0, which the constraints exclude).

## Approach: window-counts (Slide a window and compare letter counts)

### Intuition

Letter counts characterize a rearrangement just as well as sorting, and counts can be updated as the window slides: add the letter entering on the right and subtract the one leaving on the left. Comparing two arrays of 26 counts per step is cheap.

### Algorithm

1. If `m > n`, return `false`.
2. Count the letters of `pattern` into `need`.
3. For each `right` from 0 to n - 1:
   1. Add `text[right]` to `window`; if `right >= m`, remove `text[right - m]`.
   2. If `right >= m - 1` and `window == need`, return `true`.
4. Return `false`.

### Correctness

After step 3.1, `window` holds the counts of `text[max(0, right-m+1) .. right]`, by induction on `right`: one letter enters and, once the window is full, exactly one leaves. From `right = m - 1` on, that is a window of length exactly `m`, and equal counts mean it is a rearrangement of `pattern`.

### Complexity

- Time: O(a * n + m) — counting the pattern is O(m), and each of the n steps does O(1) updates plus a 26-element comparison.
- Space: O(a) — two arrays of 26 counts.

### Trade-offs

Linear and easy to write, and the comparison is a fixed 26 steps, so for this alphabet it is only a constant factor slower than `match-count`. With a large alphabet (Unicode text), the per-step comparison becomes the bottleneck, which `match-count` removes.

### Pitfalls and edge cases

- Compare only full windows (`right >= m - 1`); earlier partial windows can never match because they have fewer letters.
- Remove the letter at `right - m`, not `right - m + 1`, which is still inside the window.

### Language notes

- Python: `window == need` compares two lists element by element in C.
- TypeScript: typed arrays have no built-in equality; the reference loops over the 26 slots.
- Java: `Arrays.equals(int[], int[])` compares contents.
- Kotlin: `IntArray.contentEquals` compares contents.
- Go: `[26]int` is an array value, and arrays of comparable elements compare with `==` directly, so `window == need` needs no helper.
- Rust: `[usize; 26]` also implements `PartialEq`, so `window == need` compares all 26 counts. The count only decreases for a letter that was added earlier, so the `usize` arithmetic cannot underflow, and `right + 1 >= width` avoids the `width - 1` subtraction.

## Approach: match-count (Slide a window and track balanced letters)

### Intuition

Instead of comparing all 26 counts at every step, keep `surplus[c] = windowCount[c] - patternCount[c]` and a counter `balanced` of letters whose surplus is zero. Each slide changes the surplus of at most two letters, and each change can move only that letter into or out of the balanced set, so `balanced` updates in O(1). The window is a rearrangement exactly when all 26 letters are balanced.

### Algorithm

1. If `m > n`, return `false`.
2. Set `surplus[c] = -patternCount[c]` and `balanced` to the number of letters with surplus zero (the letters absent from the pattern).
3. Define `shift(c, delta)`: if `surplus[c]` was 0, decrease `balanced`; add `delta`; if it is now 0, increase `balanced`.
4. For each `right`: `shift(text[right], +1)`; if `right >= m`, `shift(text[right - m], -1)`; if `balanced == 26`, return `true`.
5. Return `false`.

### Correctness

`shift` keeps `balanced` equal to the number of letters with zero surplus, since only the shifted letter's status can change. Before the window is full, the window holds fewer than `m` letters while the pattern holds `m`, so the surpluses cannot all be zero: no false positive. Once full, the window has the same counts as the pattern exactly when every surplus is zero, that is, when `balanced == 26`.

### Complexity

- Time: O(n + m) — O(m) to count the pattern, O(1) per text position.
- Space: O(a) — one array of 26 surpluses.

### Trade-offs

Constant work per step regardless of the alphabet size, and the same "count of satisfied constraints" trick drives Minimum Window Substring. It is a little more code than `window-counts` and easy to get wrong in the update order; for 26 letters the speed difference is modest.

### Pitfalls and edge cases

- In `shift`, check the old value before changing it and the new value after; doing both checks after the change miscounts.
- Initialize `balanced` with the letters that do not occur in the pattern: their surplus starts at zero.
- Check `balanced == 26` after both the add and the remove of a step, not between them.

### Language notes

- Python: a nested function with `nonlocal balanced` keeps the update logic in one place.
- TypeScript: an arrow function closes over `balanced` and `surplus`.
- Java: there are no local functions in Java, so the reference keeps `surplus` and `balanced` as fields and resets them at the start of each call.
- Kotlin: a local `fun shift` can modify the enclosing `var balanced` directly.
- Go: a closure `shift` modifies the enclosing `surplus` array and `balanced` counter directly, the counterpart of Python's nested function with `nonlocal`.
- Rust: a closure that mutated both `surplus` and `balanced` would keep them borrowed while the loop reads `balanced`, so the pair lives in a small `Balance` struct and `shift` is a method. `usize::from(byte - b'a')` turns a byte into a letter index.
