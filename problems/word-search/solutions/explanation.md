# Word Search: Explanation

## Overview

In the bounds below, r and c are the board's row and column counts and L is the word length.

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| visited-grid | intermediate | O(r * c * 3^L) | O(r * c + L) | first working version; leaves the board untouched |
| pruned-in-place | optimal | O(r * c * 3^L) | O(L) | default answer: same worst case, but cheap checks remove most hopeless searches |

Both run the same depth-first search. The worst case cannot be improved in general (a board of one letter and a word that fails only at its last letter forces the search through every walk), so the optimal version wins by pruning before and during the search, not by a better bound.

## Approach: visited-grid (Depth-first search from every cell with a visited grid)

### Intuition

A walk that spells the word starts somewhere, so try every cell as the start. From a cell matching letter `k`, the rest of the word must continue from one of its four neighbors, which is the same question one letter later. A boolean grid records which cells the current walk occupies, so the walk never reuses one.

### Algorithm

1. Create a `visited` grid of `false`.
2. `spellsFrom(r, c, k)`:
   1. Return `false` if `(r, c)` is off the board, already visited, or does not hold `word[k]`.
   2. Return `true` if `k` is the last index.
   3. Mark `(r, c)` visited, try `spellsFrom` on the four neighbors with `k + 1`, unmark `(r, c)`, and return whether any neighbor succeeded.
3. Return whether `spellsFrom(r, c, 0)` succeeds for some cell.

### Correctness

`spellsFrom(r, c, k)` returns `true` exactly when some walk that starts at `(r, c)`, avoids the cells currently marked and only uses neighbor steps spells `word[k:]`. The base cases are immediate. For the recursive case, such a walk consists of `(r, c)` followed by a walk from a neighbor that spells `word[k+1:]` and avoids `(r, c)` as well, which is exactly what marking `(r, c)` before the recursive calls enforces. Unmarking afterwards restores the precondition for the caller's other branches. Trying every start cell covers every possible walk.

### Complexity

- Time: O(r * c * 3^L) — there are r * c start cells; from each, the first step has at most 4 options and every later step at most 3, because the cell just left is marked, so each start explores at most 4 * 3^(L-1) partial walks.
- Space: O(r * c + L) — the visited grid has r * c cells and the recursion is at most L calls deep.

### Trade-offs

Simple and side-effect free, which makes it the oracle. It searches blindly: a word with a letter the board lacks, or one whose first letter covers the whole board, is only rejected after a large search. The separate visited grid also costs memory that marking cells on the board itself avoids.

### Pitfalls and edge cases

- Unmark the cell after exploring its neighbors; forgetting it makes later walks fail wrongly.
- Check the letter before marking, and test "last letter" only after the letter matched, so a one-letter word on a matching cell succeeds.
- Diagonal steps are not part of the walk.

### Language notes

- Python: `any(...)` over a generator stops at the first neighbor that succeeds, which also short-circuits the search.
- TypeScript: `STEPS.some(...)` short-circuits the same way; `board[r][c]` is a one-character string compared with `word[k]`.
- Java: `char` comparison with `word.charAt(k)` avoids building strings; the explicit `break` stops after the first success.
- Kotlin: `r !in 0 until rows` reads as the bounds check; `IntArray` destructuring in `{ (dr, dc) -> ... }` works through `component1` and `component2`.
- Go: the board is `[][]rune`, so a cell compares with `letters[k]` after `[]rune(word)`. `visited` is built row by row with `make`, because `make([][]bool, rows)` only creates the outer slice. The recursive closure is declared first and assigned after, and `break` after the first success stops trying the other directions.
- Rust: the bounds check moves into a small `neighbor` helper that returns `None` for a cell off the board, using `checked_add_signed` so a step to row `-1` is `None` and never wraps. `STEPS.iter().any(..)` stops at the first neighbor that succeeds, and `vec![vec![false; cols]; rows]` makes the visited grid, cloning the inner vector for each row.

## Approach: pruned-in-place (Count letters, search from the rarer end, mark cells in place)

### Intuition

Three cheap observations remove most of the work. If the board holds fewer copies of some letter than the word needs, no walk exists at all. A walk read backwards is also a walk, so you may search for the reversed word, and starting from the rarer of the two end letters leaves far fewer starting cells alive after the first step. Finally, the board itself can serve as the visited marker: overwrite the current cell with a character that matches no letter, and restore it on the way back.

### Algorithm

1. Count the letters on the board and in the word; return `false` if the word needs more of some letter than the board has.
2. If the word's first letter is more common on the board than its last, reverse the word.
3. `spellsFrom(r, c, k)`:
   1. Return `false` if `board[r][c]` is not `word[k]` (a used cell holds `#`, which never matches).
   2. Return `true` if `k` is the last index.
   3. Write `#` into `board[r][c]`, try the in-bounds neighbors with `k + 1`, write `word[k]` back, and return whether any succeeded.
4. Return whether `spellsFrom(r, c, 0)` succeeds for some cell.

### Correctness

Step 1 only rejects words that need more copies of a letter than exist, and a walk uses distinct cells, so no walk could spell them. Step 2 is safe because reversing a walk gives a walk through the same cells, so a walk spells the word exactly when its reverse spells the reversed word. In step 3, `#` matches no lowercase letter, so overwriting a cell has the same effect as marking it visited, and writing back `word[k]` restores the original letter, since the cell matched `word[k]` in step 1. The rest of the argument is the same as for the visited grid.

### Complexity

- Time: O(r * c * 3^L) — counting costs O(r * c + L); in the worst case (every count passes and many walks fail late) the search is the same as before.
- Space: O(L) — the recursion depth and the reversed word; the letter counts have at most 26 entries and no grid is allocated.

### Trade-offs

Same worst case, but the counting check is linear and kills the classic adversarial inputs (a board of `a` and a word ending in a missing letter), and the reversal shrinks the search when one end letter is rare. Writing into the board saves the visited grid at the cost of temporarily mutating the input; restoring every cell before returning keeps the caller's board unchanged. In a multi-word variant (Word Search II) a trie replaces the per-word search.

### Pitfalls and edge cases

- Restore the cell on every path out of the call, including the successful one, or the caller's board stays corrupted.
- The sentinel must be a character that never occurs in the board or the word.
- Reverse the word, never the board.

### Language notes

- Python: `collections.Counter` subtraction is not needed; comparing per letter with `available[letter] < needed` handles missing letters, since a `Counter` returns 0 for them.
- TypeScript: `board.flat()` lists every cell for counting; `[...word].reverse().join("")` reverses the string.
- Java: arrays of 128 counters indexed by `char` replace maps; incrementing `needed` and comparing in one pass returns early on the first shortage.
- Kotlin: `groupingBy { it }.eachCount()` builds both count maps; `word.reversed()` returns the reversed string.
- Go: two `[26]int` arrays count the letters, and `letter-'a'` is the slot, since a `rune` is an integer; `slices.Reverse` reverses the `[]rune` in place. The recursion checks the `'#'` mark through the comparison with `letters[k]` alone, because the word has no `'#'`.
- Rust: two `[usize; 26]` arrays count the letters, and `available.iter().zip(&needed).any(..)` finds the first shortage. The function owns the board (`mut board`), so marking a cell with `'#'` and restoring it needs no copy; `letters.reverse()` reverses the word's characters in place.
