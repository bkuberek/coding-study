# Rotate Image: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| copy-rotated | brute | O(n^2) | O(n^2) | memory is no concern and clarity matters most |
| transpose-reverse | optimal | O(n^2) | O(1) | default in-place answer; easiest to get right |
| four-way-swap | optimal | O(n^2) | O(1) | you want one pass that moves each value exactly once |

All three read and write every cell a constant number of times, so they share the O(n^2) time of an `n x n` matrix; they differ in extra memory and in how easy the index arithmetic is to get right. The key fact is the mapping: the value at `(r, c)` moves to `(c, n - 1 - r)`.

## Approach: copy-rotated (Build the rotated copy and write it back)

### Intuition

Write the definition down directly: the rotated image's cell `(r, c)` takes the original value at `(n - 1 - c, r)`. Building a separate matrix means no value is overwritten before it is read.

### Algorithm

1. Create `rotated` with `rotated[r][c] = matrix[n - 1 - c][r]` for every cell.
2. Copy `rotated` back into `matrix`, row by row.

### Correctness

Inverting the mapping `(r, c) -> (c, n - 1 - r)` gives `(r, c) <- (n - 1 - c, r)`, which is what step 1 reads. Every read comes from the untouched original, so the copy is exactly the rotated image, and step 2 makes `matrix` equal to it.

### Complexity

- Time: O(n^2) — every cell is read once and written twice.
- Space: O(n^2) — the second matrix.

### Trade-offs

Hard to get wrong, which makes it the oracle, but it uses as much extra memory as the image itself, and the problem asks for an in-place rotation. In an interview it is a fine first answer to state before improving on memory.

### Pitfalls and edge cases

- The result must end up in the caller's matrix. Rebinding a local variable (`matrix = rotated` in Python) changes nothing for the caller; assign into it instead (`matrix[:] = rotated`, `System.arraycopy`, `copyInto`).

## Approach: transpose-reverse (Transpose then reverse every row)

### Intuition

A quarter turn clockwise equals two reflections: first across the main diagonal (the transpose, `(r, c) -> (c, r)`), then left to right (`(r, c) -> (r, n - 1 - c)`). Composing them sends `(r, c)` to `(c, r)` and then to `(c, n - 1 - r)`, the rotation. Each reflection is easy to do in place with swaps.

### Algorithm

1. For every pair `r < c`, swap `matrix[r][c]` with `matrix[c][r]`.
2. Reverse every row.

### Correctness

Step 1 swaps each off-diagonal pair once (only `c > r` is visited) and leaves the diagonal alone, which is the transpose. Step 2 mirrors each row. As shown above, the composition maps every value from `(r, c)` to `(c, n - 1 - r)`, the clockwise quarter turn.

### Complexity

- Time: O(n^2) — about `n^2 / 2` swaps for the transpose and `n^2 / 2` for the reversals.
- Space: O(1) — one temporary value per swap.

### Trade-offs

The usual interview answer: in place, short and easy to verify, since each step is a familiar operation. It moves each value twice instead of once, which does not change the complexity. Variants follow the same recipe: reversing the rows first and then transposing gives a counterclockwise turn.

### Pitfalls and edge cases

- Swapping every pair, including `c < r`, transposes twice and restores the original; start the inner loop at `r + 1`.
- Reversing columns instead of rows after the transpose gives the counterclockwise rotation.

### Language notes

- Python: tuple assignment swaps without a temporary; `list.reverse()` mirrors a row in place.
- TypeScript: `Array.prototype.reverse` reverses in place as well.
- Java: no built-in in-place reversal for `int[]`, so the reference swaps from both ends; `Collections.reverse` would need boxed lists.
- Kotlin: `IntArray.reverse()` reverses in place, unlike `reversed()`, which returns a new list.
- Go: the tuple assignment `matrix[r][c], matrix[c][r] = matrix[c][r], matrix[r][c]` swaps without a temporary, and `slices.Reverse(row)` reverses a row in place; a row of a `[][]int` is a slice header into shared memory, so the caller sees the change.
- Rust: swapping `matrix[r][c]` with `matrix[c][r]` needs two `&mut` borrows of `matrix` at once, which the borrow checker refuses. `split_at_mut(r + 1)` splits the rows into row `r` and the rows below it, which are disjoint, so `std::mem::swap` can hold one cell from each. `row.reverse()` reverses in place. The stub takes `&mut Vec<Vec<i32>>` and this reference only uses slice operations, so clippy's `ptr_arg` is allowed on the function.

## Approach: four-way-swap (Cycle four cells at a time, layer by layer)

### Intuition

Apply the mapping repeatedly: a cell in the top edge goes to the right edge, then to the bottom edge, then to the left edge, then back. Those four cells form a cycle, so rotating them needs a single temporary value. The matrix splits into concentric square layers, and each layer splits into such 4-cycles.

### Algorithm

1. For each layer `layer` from 0 to `n / 2 - 1`, let `last = n - 1 - layer`.
2. For each `offset` from 0 to `last - layer - 1`:
   1. Save `top = matrix[layer][layer + offset]`.
   2. Move left into top, bottom into left, right into bottom: `matrix[layer][layer + offset] = matrix[last - offset][layer]`, `matrix[last - offset][layer] = matrix[last][last - offset]`, `matrix[last][last - offset] = matrix[layer + offset][last]`.
   3. Put the saved value into the right cell: `matrix[layer + offset][last] = top`.

### Correctness

With `n - 1 - last = layer`, the mapping `(r, c) -> (c, n - 1 - r)` sends the left cell `(last - offset, layer)` to the top cell `(layer, layer + offset)`, the bottom cell `(last, last - offset)` to the left cell, the right cell `(layer + offset, last)` to the bottom cell, and the top cell to the right cell. Step 2 performs exactly those four moves. As `offset` runs from 0 to `last - layer - 1`, the top cells cover the layer's top edge except its last corner, so every cell of the layer is in exactly one cycle; the layers cover the matrix, and the centre of an odd matrix is a cycle of length one that stays put.

### Complexity

- Time: O(n^2) — each cell is moved exactly once.
- Space: O(1) — one temporary per cycle.

### Trade-offs

Moves each value once, the minimum, but the four index expressions are easy to mix up, which is why transpose-then-reverse is usually preferred under time pressure. It also generalizes poorly to other rotations compared to combining reflections.

### Pitfalls and edge cases

- The inner loop runs to `last - layer - 1`, not `last - layer`: the last corner of the top edge is already the first cell of the right edge.
- Odd sides have a centre cell that no layer touches; even sides have none. Test both (sides 4 and 5).
- Doing the four moves in the wrong order overwrites a value before it is read; derive the order from the mapping rather than by symmetry.

### Language notes

- All four references are line-for-line the same algorithm; only loop syntax differs (`range`, `for (let ...)`, `0 until n / 2`). Integer division `n // 2`, `Math.floor(n / 2)` and `n / 2` on `int` all round down.
- Go: the same loops with C-style `for` headers; the four assignments run in the order the comment gives.
- Rust: indexes are `usize`, and the subtractions `n - 1 - layer` and `last - layer` cannot underflow because `layer < n / 2` and `last >= layer`. Each move is a plain `matrix[a][b] = matrix[c][d]`, which copies an `i32`, so no temporary borrow is needed; `ptr_arg` is allowed for the same reason as in `transpose-reverse`.
