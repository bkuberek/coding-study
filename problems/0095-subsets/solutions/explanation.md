# Subsets: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| bitmask | optimal | O(n * 2^n) | O(n * 2^n) | n fits in a machine word and you want a loop instead of recursion |
| backtracking | optimal | O(n * 2^n) | O(n * 2^n) | default interview answer; the same skeleton solves the rest of the pattern |

Every answer must write out 2^n subsets whose total length is n * 2^(n-1), so no approach can beat O(n * 2^n). Both approaches reach that bound; they differ in how they enumerate the in-or-out choices.

## Approach: bitmask (Read each subset from the bits of a counter)

### Intuition

A subset is a sequence of n yes-or-no decisions, one per value. The binary representations of the integers 0 to 2^n - 1 are exactly all sequences of n bits, each once. Read bit `i` as "is `nums[i]` in?" and counting from 0 to 2^n - 1 lists every subset.

### Algorithm

1. For each `mask` from 0 to 2^n - 1:
   1. Start an empty subset.
   2. For each index `i`, append `nums[i]` when bit `i` of `mask` is set.
   3. Add the subset to the result.
2. Return the result.

### Correctness

The map from masks to subsets is a bijection: two different masks differ in some bit `i`, so exactly one of their subsets contains `nums[i]` (the values are distinct), and every subset is produced by the mask whose bits mark its members. Hence each of the 2^n subsets appears exactly once.

### Complexity

- Time: O(n * 2^n) — 2^n masks, and each mask tests n bits and copies at most n values.
- Space: O(n * 2^n) — the output holds 2^n subsets with n * 2^(n-1) values in total; besides the output only the loop counters are used.

### Trade-offs

No recursion and no shared mutable state, which makes it short and easy to trust, so it serves as the oracle. It needs `n` below the word size (31 for an `int`), which the constraints guarantee by a wide margin. It does not extend to pruning: variants that skip branches (target sums, duplicates) need the recursive form.

### Pitfalls and edge cases

- Loop to `1 << n` exclusive; `<=` produces an extra, wrong subset.
- Mask 0 is the empty subset and must be included.
- In languages with operator precedence surprises, parenthesize `(mask >> i) & 1`.

### Language notes

- Python: `mask >> i & 1` parses as `(mask >> i) & 1` because shifts bind tighter than `&`.
- TypeScript: `nums.filter((_, i) => ((mask >> i) & 1) === 1)` keeps the values whose bit is set; bit operators work on 32-bit integers, which is plenty for n at most 10.
- Java: a nested loop fills an `ArrayList<Integer>`; `List<List<Integer>>` matches the signature.
- Kotlin: `shr` and `and` are infix functions, and `filterIndexed` reads like the Python comprehension.
- Go: `1<<len(nums)` is the number of masks, and `mask>>i&1 == 1` reads bit `i` (in Go the shift and the `&` have the same precedence and group left to right, so no parentheses are needed). The empty subset stays a `nil` slice, which the encoder writes as `[]`.
- Rust: `1u32 << nums.len()` needs the `u32` suffix so the range has a type. Unlike C, Rust ranks `&` above `==`, so `(mask >> i) & 1 == 1` already means `((mask >> i) & 1) == 1`; the parentheses around the shift only make the order easy to read. `collect()` builds each inner `Vec` and then the outer one.

## Approach: backtracking (Choose or skip each value)

### Intuition

Walk the values in order and make the decision for one value per level of recursion: first include it and explore everything that follows, then undo that choice and explore again without it. The recursion tree is a complete binary tree of depth n whose 2^n leaves are the subsets.

### Algorithm

1. Keep one shared list `chosen` and a result list.
2. `explore(index)`:
   1. If `index == n`, append a copy of `chosen` to the result and return.
   2. Append `nums[index]` to `chosen`, call `explore(index + 1)`, then remove it again.
   3. Call `explore(index + 1)` without it.
3. Call `explore(0)` and return the result.

### Correctness

By induction on the depth: when `explore(index)` is called, `chosen` holds a fixed choice for `nums[0..index-1]`, and the call appends that choice extended by every combination of in-or-out for `nums[index..n-1]`, each once. The two branches differ in whether `nums[index]` is present, so they never produce the same subset. At `index = 0` this is every subset exactly once. Removing the value after the first branch restores `chosen`, which is what makes the second branch start from the right state.

### Complexity

- Time: O(n * 2^n) — the recursion tree has 2^(n+1) - 1 calls, each doing O(1) work besides the leaf copies, and copying the 2^n leaves costs O(n) each.
- Space: O(n * 2^n) — the output dominates; the recursion depth and `chosen` add only O(n).

### Trade-offs

Same asymptotic cost as the bitmask, with a slightly higher constant for the calls. Its value is the shape: adding a pruning test, a "skip equal siblings" rule or a running sum turns it into Subsets With Duplicates, Combination Sum or Palindrome Partitioning. An iterative cascade (start with `[[]]`, and for each value append it to a copy of every subset so far) is a third O(n * 2^n) option without recursion.

### Pitfalls and edge cases

- Append a copy of `chosen` at the leaf; appending the shared list itself leaves every entry pointing at the same (finally empty) list.
- Undo the choice (`pop`) before exploring the "skip" branch.
- Emitting at every node instead of only at leaves is another valid scheme (each node is a subset of the values chosen so far), but mixing the two schemes produces duplicates.

### Language notes

- Python: `chosen.copy()` (or `chosen[:]`) snapshots the list; a nested function closes over `result` and `chosen`.
- TypeScript: `[...chosen]` copies; an arrow function closure keeps the recursion local.
- Java: `new ArrayList<>(chosen)` copies; `chosen.remove(chosen.size() - 1)` removes by index (an `int` argument), not by value.
- Kotlin: `chosen.toList()` copies into a read-only list; a local `fun` can recurse and capture `result`.
- Go: a recursive closure has to be declared first (`var explore func(index int)`) and assigned after, so it can call itself. `chosen = chosen[:len(chosen)-1]` undoes the append, and `slices.Clone(chosen)` snapshots the current choice, because the slice header shares its backing array with later appends.
- Rust: the recursion is a function taking `chosen` and `result` as `&mut Vec`, which passes the same buffers down without copying them; `chosen.clone()` snapshots the current choice into `result`, and `chosen.pop()` undoes the push.
