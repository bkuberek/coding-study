# Move Zeroes: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| buffer | brute | O(n) | O(n) | memory is free and clarity matters most, or as a correctness oracle |
| write-index | optimal | O(n) | O(1) | default answer |
| swap | optimal | O(n) | O(1) | zeros are rare and writes are expensive |

## Approach: buffer (Copy the non-zeros into a buffer)

### Intuition

The final array is easy to describe: the non-zero values in order, then zeros. Building that array separately and copying it back over `nums` needs no cleverness at all.

### Algorithm

1. Collect the non-zero values of `nums`, in order, into a new list `nonZero`.
2. Write `nonZero` into `nums[0 .. k-1]`, where `k = len(nonZero)`.
3. Write `0` into `nums[k .. n-1]`.

### Correctness

Step 1 preserves the relative order of the non-zero values because it reads `nums` left to right and appends. The array has n positions and k of them hold non-zero values, so exactly n - k zeros follow, matching the original count of zeros. Because the buffer is a separate list, writing into `nums` in steps 2 and 3 cannot overwrite a value that still has to be read.

### Complexity

- Time: O(n) — one pass to filter and one pass to write back.
- Space: O(n) — the buffer holds up to n values.

### Trade-offs

Correct at a glance and linear, but it allocates a second array, which the statement asks you to avoid. It is the oracle because it has no index interplay to get wrong. In an interview it is a fine first sentence; the in-place versions are what is being tested.

### Pitfalls and edge cases

- In Python, `nums = non_zero + zeros` rebinds the local name and leaves the caller's list unchanged. Assign through the slice, `nums[:] = ...`, to mutate it.
- An all-zero array gives an empty buffer; the write-back must still fill every position with zero.
- Negative values are non-zero: filter with `!= 0`, not `> 0`.

### Language notes

- Python: a list comprehension filters, and slice assignment replaces the list's contents in place.
- TypeScript: `Array.prototype.filter` builds the buffer; a plain index loop writes it back. Avoid `nums.splice(0, n, ...nonZero)`: spreading 10^5 arguments into one call can exceed the engine's argument limit.
- Java: a new `int[]` starts filled with zeros, so copying the compacted buffer over `nums` with `System.arraycopy` also writes the trailing zeros.
- Kotlin: `IntArray.filter` returns a boxed `List<Int>`; `fill(0, fromIndex)` zeroes the tail.
- Go: the function has no result, so it edits the caller's slice in place: `copy(nums, nonZero)` writes the compacted prefix and the builtin `clear` zeroes the rest of the slice.
- Rust: the result goes back through the `&mut Vec<i32>` parameter. The code collects the non-zero values, pads them with zeros to the original length and assigns the new vector with `*nums = buffer`, the counterpart of Python's `nums[:] = ...`.

## Approach: write-index (Compact forward then fill with zeros)

### Intuition

The k-th non-zero value (counting from 0) belongs at index k. Keep a `write` index that counts the non-zero values seen so far; each new non-zero value is copied to `nums[write]`. Since `write` never passes the reading position, nothing unread is overwritten. Whatever lies at or after `write` once the scan ends must become zero.

### Algorithm

1. Set `write = 0`.
2. For each value of `nums`, left to right: if it is non-zero, set `nums[write] = value` and increase `write`.
3. Set every position from `write` to n - 1 to `0`.

### Correctness

Invariant: after reading position `r`, `nums[0 .. write-1]` holds the non-zero values of the original `nums[0 .. r]`, in order. A non-zero value extends that prefix by one; a zero leaves it unchanged. The write position `write` is at most `r`, so the write in step 2 lands on a position that has already been read, and every later read still sees an original value. After the scan the prefix holds all non-zero values in order; step 3 makes the remaining n - write positions zero, which is exactly the number of zeros in the input.

### Complexity

- Time: O(n) — one scan plus one fill, each touching every position at most once.
- Space: O(1) — one index.

### Trade-offs

The simplest in-place version and the usual interview answer. It writes every non-zero value once (even ones already in place) and then writes every trailing zero, so it performs about n writes regardless of the input. The `swap` approach avoids writes for values that are already in place.

### Pitfalls and edge cases

- Do not skip step 3: without it, the tail keeps stale copies of values that were moved forward. `[0, 1]` would become `[1, 1]`.
- Reading with a `for value in nums` loop while writing at `write` is safe only because `write <= r`; a version that writes ahead of the reader would corrupt the input.
- With no zeros, every value is copied onto itself and the fill does nothing.

### Language notes

- Python: iterating with `for value in nums` while assigning to earlier indices is safe; the iterator reads by position and the list does not change length.
- TypeScript: `Array.prototype.fill(0, write)` zeroes the tail in one call.
- Java: `Arrays.fill(nums, write, nums.length, 0)` zeroes the tail; the end index is exclusive.
- Kotlin: `nums[write++] = value` uses the old value of `write`, as in Java, and `IntArray.fill(0, write)` zeroes the tail.
- Go: `for _, value := range nums` reads each element when its iteration starts, so writing at the lagging `write` index behind it is safe; `clear(nums[write:])` zeroes the tail in one call.
- Rust: a `for value in nums.iter()` loop would hold a shared borrow of the vector while the body writes to it, so the loop indexes by `read` instead; `nums[write..].fill(0)` zeroes the tail.

## Approach: swap (Swap each non-zero into the next free slot)

### Intuition

Same two indices as `write-index`, but instead of copying a non-zero value forward and fixing the tail later, swap it with whatever sits at `write`. The positions between `write` and the reader always hold zeros, so the swap moves a zero backwards and the tail never needs a separate fill.

### Algorithm

1. Set `write = 0`.
2. For `read` from 0 to n - 1: if `nums[read]` is non-zero, swap `nums[write]` and `nums[read]`, then increase `write`.

### Correctness

Invariant: after processing position `read`, `nums[0 .. write-1]` holds the non-zero values of the original `nums[0 .. read]` in order, and `nums[write .. read]` holds only zeros. A zero at `read` extends the zero block by one. A non-zero value at `read` is swapped with `nums[write]`, which is either a zero from the block (when `write < read`) or the value itself (when `write == read`); either way the prefix grows by that value in order and the zero block shifts right by one. At the end the zero block runs from `write` to n - 1. Swaps only permute values, so the count of zeros is unchanged.

### Complexity

- Time: O(n) — one scan with at most one swap per position.
- Space: O(1) — one index and a temporary for the swap.

### Trade-offs

Same growth as `write-index` and no tail fill. When `write == read` (no zero seen yet) the swap is a self-swap; a guard `if write != read` turns those into no writes, which matters when writes are costly and zeros are rare. When zeros are common, each swap writes two positions, so `write-index` does fewer writes. In practice both are equally good interview answers; mentioning the write-count difference is a strong follow-up.

### Pitfalls and edge cases

- Increase `write` only after a swap of a non-zero value, never on zeros.
- A self-swap at `write == read` is harmless; do not "optimize" it by skipping the increase of `write`.
- The zero block between `write` and `read` is what makes the swap safe; if the invariant is unclear, trace `[0, 1, 0, 3]` by hand.

### Language notes

- Python: tuple assignment `nums[write], nums[read] = nums[read], nums[write]` swaps without a temporary.
- TypeScript: destructuring `[nums[write], nums[read]] = [nums[read], nums[write]]` allocates a small array per swap; a temporary variable is faster in hot loops.
- Java: an explicit temporary `int` is the idiom; there is no swap helper for `int[]` in the standard library.
- Kotlin: `nums[write] = nums[read].also { nums[read] = nums[write] }` swaps in one expression: the right side is read before the `also` block overwrites `nums[read]`.
- Go: the tuple assignment `nums[write], nums[read] = nums[read], nums[write]` swaps without a temporary; when `write == read` it swaps a slot with itself, which does nothing.
- Rust: `Vec::swap(write, read)` exchanges two slots by index and accepts equal indexes; the standard library's `swap` avoids the two overlapping mutable borrows that `std::mem::swap(&mut nums[a], &mut nums[b])` would need.
