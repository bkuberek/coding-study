# Minimum Window Substring: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n^2 + m) | O(a) | n is small, or as a correctness oracle |
| sliding-window | optimal | O(n + m) | O(a) | default answer |
| filtered-window | optimal | O(n + m) | O(n) | `t` uses few letters and most of `s` is irrelevant |

Here `n` is the length of `s`, `m` the length of `t` and `a` the alphabet size (52 letters; the references index arrays by ASCII code, 128 slots). Every approach uses the same bookkeeping: per letter, how many more copies the window needs (its deficit, negative when the window has extra copies), and `missing`, the total number of copies still needed. A window covers `t` exactly when `missing == 0`.

## Approach: brute-force (Extend from every start until t is covered)

### Intuition

For each start, extend the window one letter at a time until it covers `t`. That is the shortest covering window with this start, since longer ones only add letters. Keep the shortest over all starts; scanning starts from left to right and replacing only on a strictly shorter window keeps the leftmost one on ties.

### Algorithm

1. Count the letters of `t` into `need`.
2. For each `start`:
   1. Copy `need` into `remaining` and set `missing = m`.
   2. For each `end` from `start`: if `remaining[s[end]] > 0`, decrease `missing`; decrease `remaining[s[end]]`. When `missing == 0`, record the window if it is strictly shorter than the best, and stop this start.
3. Return the best window, or `""` if none was recorded.

### Correctness

`missing` counts the copies of `t`'s letters that `s[start .. end]` still lacks: a letter reduces it only while its own deficit is positive, so surplus copies do not count. For a fixed start, coverage is monotone in `end`, so the first covering `end` gives the shortest window with this start. The overall shortest window has some start and is found there. Starts are visited in increasing order and only strictly shorter windows replace the best, so among equally short windows the leftmost is kept.

### Complexity

- Time: O(n^2 + m) — counting `t` is O(m); each of the n starts can scan to the end. The generator plants a rare letter that `t` needs one to four times, so covering windows are long and the scans are long at every seed. Copying the counts per start adds O(a) per start.
- Space: O(a) — two count tables.

### Trade-offs

Correct and simple, hence the oracle, but every start recounts letters the previous start already saw. At n = 10^4 it does on the order of 10^7 steps.

### Pitfalls and edge cases

- Count repeats: `t = "aa"` needs two `a`s; a set of letters is not enough.
- If `t` is longer than `s`, or needs more copies of a letter than `s` has, the answer is `""`.
- Uppercase and lowercase letters are distinct: `aA` with `t = "A"` gives `A`.
- Replace the best only on a strictly shorter window, or ties resolve to the rightmost window.

### Language notes

- Python: `Counter(t)` builds the counts and `dict(need)` copies them per start; letters not in `t` are skipped with `dict.get`.
- TypeScript: `Int32Array(128).slice()` copies the table per start; `remaining[code]-- > 0` tests and decrements in one step.
- Java: `int[128]` with `clone()` per start; a `char` indexes the array directly.
- Kotlin: `IntArray.copyOf()` per start and `Char.code` as the index.
- Go: `[128]int` is an array value, so `remaining := need` copies all 128 counts in one assignment; indexing a string yields bytes, which are whole letters here. The result is a substring of `s`, which shares its bytes and copies nothing.
- Rust: `[i32; 128]` is `Copy`, so `let mut remaining = need;` copies the table. Counts for letters absent from `t` start at 0 and go negative, which never triggers `missing -= 1`. The answer is a byte-range slice of `s`, converted to an owned `String` once at the end.

## Approach: sliding-window (Expand to cover and shrink to the minimum)

### Intuition

Move a right edge across `s`. Each letter it adds lowers its deficit, and if that deficit was positive, the window needed it, so `missing` drops. Once `missing` reaches 0 the window covers `t`; now move the left edge right as long as the window still covers `t`, recording each window, because each is shorter than the one before. When removing a letter makes its deficit positive again, the window stops covering and the right edge resumes.

### Algorithm

1. Set `deficit[c]` to the count of `c` in `t`, `missing = m`, `left = 0`, and the best window to empty.
2. For each `right`:
   1. If `deficit[s[right]] > 0`, decrease `missing`. Decrease `deficit[s[right]]`.
   2. While `missing == 0`: record `[left, right]` if strictly shorter than the best; increase `deficit[s[left]]`, and if it becomes positive, increase `missing`; increase `left`.
3. Return the best window, or `""`.

### Correctness

Invariant: `deficit[c]` equals the count of `c` in `t` minus its count in `s[left .. right]`, and `missing` equals the sum of the positive deficits, so `missing == 0` exactly when the window covers `t`. For each `right`, the inner loop moves `left` to one past the largest start whose window to `right` still covers `t`, recording that shortest covering window ending at `right`. `left` never needs to move back: a start that fails to cover with some `right` was dropped only after a covering window from it had been recorded, and any longer window from it is not shorter. The overall shortest window ends at some `right` and is recorded there. Windows are recorded in increasing order of `right`; two equally short windows with different starts have different ends, so the leftmost one is recorded first and strict comparison keeps it.

### Complexity

- Time: O(n + m) — counting `t` is O(m); `right` and `left` each advance at most n times, with O(1) work per step.
- Space: O(a) — one deficit table.

### Trade-offs

The canonical "minimum window" template: expand until valid, shrink while valid. The single `missing` counter replaces a full comparison of letter counts at every step, which is what makes it linear regardless of the alphabet. It is the expected interview answer; the subtle parts are the order of the deficit checks and recording before shrinking.

### Pitfalls and edge cases

- Check the deficit before decrementing when a letter enters, and after incrementing when it leaves; swapping the order miscounts `missing`.
- Letters not in `t` go negative and never affect `missing`, which is why their counts can stay in the same table.
- Record the window inside the shrink loop, before removing the left letter.
- Store the start and length, and slice once at the end, instead of building a substring per improvement.

### Language notes

- Python: a 128-slot list indexed by `ord` is faster than a dictionary in this hot loop.
- TypeScript: `Int32Array(128)`; `deficit[code]-- > 0` and `++deficit[code] > 0` fold the check and the update into one expression each.
- Java: the same idioms on an `int[128]`; `substring` once at the end.
- Kotlin: `IntArray(128)` indexed by `Char.code`; postfix and prefix increments work on array elements as in Java.
- Go: one `[128]int` table of deficits, indexed by the byte itself; `missing` counts the letters of `t` still uncovered, and the answer is the substring `s[bestStart : bestStart+bestLength]`.
- Rust: the table is `[i32; 128]` because deficits go negative for surplus letters, while `missing` is a `usize` that only moves when a deficit crosses zero. `right + 1 - left` is the window length, and `to_string()` turns the final `&str` slice into the owned `String` the signature returns.

## Approach: filtered-window (Slide over the positions of useful letters only)

### Intuition

Letters that do not occur in `t` never change `missing`, and a shortest window never starts or ends on one (trimming it would give a shorter window). So collect the positions of the useful letters first and run the same sliding window over that list, using the original positions to measure lengths. When `s` is long and `t` uses few distinct letters, the window moves over far fewer elements.

### Algorithm

1. Build the deficit table from `t`.
2. Collect `useful`, the positions `i` with `s[i]` in `t`, in increasing order.
3. Run the sliding window over `useful`: the right edge takes each position in turn and the left edge is an index into `useful`. A window from `useful[left]` to the current position has length `position - useful[left] + 1`.
4. Return the best window, or `""`.

### Correctness

Every shortest covering window starts and ends on a useful letter: otherwise dropping its first or last letter keeps it covering and makes it shorter. The windows over `useful` are exactly the windows of `s` that start and end on useful letters, with the same letter counts for the letters of `t`. So the sliding-window argument applies unchanged, including the leftmost tie-break, since positions are visited in increasing order.

### Complexity

- Time: O(n + m) — one pass to filter, then a sliding window over at most n positions.
- Space: O(n) — the list of useful positions, in the worst case all of `s`.

### Trade-offs

Same growth as `sliding-window` but often faster in practice when most of `s` is irrelevant, at the cost of O(n) extra memory. When every letter of `s` is useful it is strictly worse: the same work plus a list. Worth mentioning as a follow-up rather than as the first answer.

### Pitfalls and edge cases

- Measure lengths with the original positions, not with indexes into `useful`.
- Decide usefulness from the counts of `t` before the window modifies them.
- An empty `useful` list (no letter of `t` occurs in `s`) returns `""`.

### Language notes

- Python: a list of `(position, letter)` pairs keeps both at hand; `ch in deficit` on the `Counter` tests whether a letter occurs in `t`.
- TypeScript: a `number[]` of positions; the letter is re-read with `charCodeAt`.
- Java: `List<Integer>` boxes the positions; an `int[]` of size n with a length counter avoids that if memory matters.
- Kotlin: `s.indices.filter { ... }` builds a `List<Int>` of positions.
- Go: a `[]int` of positions of letters that occur in `t`, built in one pass from the same deficit table; the loop ranges over those positions only, and `useful[left]` is the start of the window.
- Rust: the positions come from an iterator chain (`enumerate`, `filter`, `map`, `collect`) over the bytes, and `for &right in &useful` borrows them. The `Vec<usize>` costs O(n) memory, which is the declared space of this approach.
