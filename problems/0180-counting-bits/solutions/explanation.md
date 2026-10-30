# Counting Bits: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| count-each | brute | O(n log n) | O(1) | you already have a popcount routine and n is small |
| half-plus-low-bit | optimal | O(n) | O(1) | default answer |

Space counts memory beyond the `n + 1` output entries, which every approach must produce. The optimal approach is a one-line dynamic program: each count is computed from the count of a smaller number that is already in the output.

## Approach: count-each (Count the bits of every number separately)

### Intuition

Apply a single-number popcount, such as the "clear the lowest set bit" loop from Count Set Bits, to every number from 0 to `n`.

### Algorithm

1. For each `i` from 0 to `n`:
   1. Count the set bits of `i` (repeatedly clear the lowest set bit, or count the 1s of its binary string).
   2. Store the count at `bits[i]`.
2. Return `bits`.

### Correctness

Each entry is computed directly from the definition by a correct popcount (see Count Set Bits for why `i & (i - 1)` clears exactly one set bit).

### Complexity

- Time: O(n log n) — a number below `n` has at most `log2(n) + 1` bits, so each count costs O(log n) steps; on average about half of them are set.
- Space: O(1) — beyond the output, one counter.

### Trade-offs

Reuses a known routine and needs no insight, but ignores how the counts relate. With a hardware popcount (`Integer.bitCount`, `int.bit_count`) each count is O(1) and this becomes linear too, but the exercise is to find the recurrence.

### Pitfalls and edge cases

- The output has `n + 1` entries, including 0; `n = 0` returns `[0]`.

### Language notes

- Python: `bin(i).count("1")` counts in C over the binary string; it is still O(log n) per number.
- TypeScript, Java, Kotlin: the inner loop `word &= word - 1` runs once per set bit.
- Go: the same inner loop as the JVM languages, `for word := i; word != 0; word &= word - 1`, with the update clause doing the bit clearing. `bits.OnesCount` from `math/bits` is a single instruction on most CPUs, so using it here would turn the approach into O(n) and hide the O(log n) per number that it exists to show.
- Rust: the same loop inside a `map` closure that `collect`s the `n + 1` counts into a `Vec<i32>`. `i32::count_ones` is the built-in, left out for the same reason as in Go.

## Approach: half-plus-low-bit (Reuse the count of i / 2 and add the lowest bit)

### Intuition

Shifting `i` right by one drops its lowest bit and keeps all the others. So `i` has exactly the set bits of `i >> 1`, plus one more if its lowest bit is 1. Since `i >> 1 < i` for `i >= 1`, filling the array in increasing order makes that earlier count available when it is needed.

### Algorithm

1. Create `bits` with `n + 1` zeros (`bits[0] = 0`).
2. For `i` from 1 to `n`: `bits[i] = bits[i >> 1] + (i & 1)`.
3. Return `bits`.

### Correctness

By strong induction on `i`. The base `bits[0] = 0` is right. For `i >= 1`, the binary form of `i` is the binary form of `i >> 1` followed by the bit `i & 1`, so `popcount(i) = popcount(i >> 1) + (i & 1)`. The index `i >> 1` is smaller than `i`, so `bits[i >> 1]` was already set correctly when step 2 reaches `i`.

### Complexity

- Time: O(n) — one shift, one mask and one addition per entry.
- Space: O(1) — nothing beyond the output.

### Trade-offs

Linear, branch-free and short: the expected answer. An equivalent recurrence uses the lowest-set-bit identity instead, `bits[i] = bits[i & (i - 1)] + 1`, since `i & (i - 1) < i` has exactly one set bit fewer. Another one uses the highest power of two `p <= i`: `bits[i] = bits[i - p] + 1`. All three are dynamic programming over the same table.

### Pitfalls and edge cases

- Fill in increasing order; the recurrence reads smaller indexes only.
- `(i & 1)` needs parentheses in most languages, because `+` binds more tightly than `&` in Java, TypeScript and Python.
- Allocate `n + 1` entries; `bits[n]` is part of the answer.

### Language notes

- Python: `i >> 1` and `i & 1` work on unbounded integers; a preallocated list avoids repeated appends.
- TypeScript: `i >> 1` is a 32-bit operation, which is exact for `i <= 10^6`.
- Java: `new int[n + 1]` is zero-filled, so `bits[0] = 0` needs no statement.
- Kotlin: shifts and masks are infix functions, `i shr 1` and `i and 1`; `IntArray(n + 1)` starts zero-filled.
- Go: `make([]int, n+1)` is zero-filled, so `bits[0]` needs no statement. In Go `&` binds tighter than `+`, as `*` does (unlike C and Java), so the parentheses in `bits[i>>1] + (i & 1)` are for the reader, not the compiler.
- Rust: `vec![0; n + 1]` is zero-filled. Indexes are `usize`, so `n` is cast once, and `(i & 1) as i32` converts the low bit for the `Vec<i32>`. In Rust `&` binds looser than `+`, so there the parentheses are required.
