# Debug: Append Aliasing: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| clone-on-store | optimal | O(2^n + C(n, k) * k) | O(C(n, k) * k) | default answer: copy a bundle at the moment it is kept |

## Approach: clone-on-store (Copy each bundle when storing it)

### Intuition

A Go slice is a small header (pointer, length, capacity) over a backing array. `append(bundle, x)` writes `x` into the backing array of `bundle` whenever `bundle` has spare capacity, and returns a new header over the *same* array. It allocates a new array only when the capacity is used up.

The loop hands `append(bundle, items[i])` to one recursive call per `i`. When `bundle` has spare capacity, every sibling writes its item into the same slot of the same array. The bundle that the first sibling stored in `bundles` is still a view of that array, so the next sibling overwrites its last item. That is the ticket: `1, 2, 3, 4` was stored, then the sibling for `5` wrote over the fourth slot, and both stored bundles now read `1, 2, 3, 5`. The print statement ran before the overwrite, so it showed the right value.

Whether a size fails depends on how `append` grows capacity: 1, 2, 4, 8, 16. A bundle of 3 items has capacity 4, so the four-item bundles built from it share one array (size 4 fails). A bundle of 4 items has capacity 4, full, so each five-item bundle gets a fresh array (size 5 passes). Sizes 6, 7 and 8 grow from capacity 8 with room to spare and fail; size 9 grows from a full 8 and passes.

The fix is to store a slice that owns its elements: `slices.Clone(bundle)`.

### Debugging approach

1. **Compare the result with the prints.** Print each bundle when it is stored, and print `bundles` once more before returning. The stored values change after they were stored, so something else writes to the same memory.
2. **Map the failing sizes.** Sizes 1, 2, 3, 5 and 9 pass, sizes 4, 6, 7 and 8 fail. A pattern that follows powers of two points at slice capacity growth.
3. **Print length and capacity.** `fmt.Println(len(bundle), cap(bundle))` before the loop shows `3 4` above every failing level: one free slot that all siblings write into.
4. **Prove the sharing.** `&bundles[0][0] == &bundles[1][0]` is `true` for the two broken bundles: they are two headers over one array.
5. **Fix where the slice escapes.** The recursion may share freely while a bundle is being built; the bug is keeping a shared view. Copy at the one place a bundle is kept.

### Algorithm

1. Start the recursion with an empty bundle and position 0.
2. If the bundle has `size` items, append a copy of it (`slices.Clone`) to `bundles` and return.
3. Otherwise, for each position `i` from `start` to the end, recurse with position `i + 1` and the bundle extended by `items[i]`.
4. Return `bundles`.

### Correctness

The recursion chooses positions in increasing order, so it visits every set of `size` positions exactly once, in lexicographic order, and each bundle lists its items in catalog order. Sharing during the recursion is harmless: when a call stores its bundle, the slots it reads hold exactly the items on its path, because a sibling overwrites slot `d` only after the previous sibling's whole subtree has finished. The stored copy owns its array, so no later write can reach it, and every stored bundle keeps the value it had at the moment it was stored.

### Complexity

- Time: O(2^n + C(n, k) * k) — the recursion visits every set of at most k positions, at most 2^n calls, and each of the C(n, k) bundles is copied in k steps.
- Space: O(C(n, k) * k) — the output; the recursion itself needs O(k).

### Trade-offs

Cloning at the store is the smallest correct change, and it puts the copy where the slice escapes the recursion, which is where a reviewer looks. Two other fixes work but are weaker. Making every recursive call allocate (`extend(i+1, append(slices.Clone(bundle), items[i]))`) copies at every internal node instead of only at the leaves. The full slice expression `append(bundle[:len(bundle):len(bundle)], items[i])` caps the capacity so that `append` must allocate, which is correct but obscure and easy to undo in a refactor. A single buffer with explicit backtracking (`bundle = bundle[:len(bundle)-1]`) allocates nothing while building and still needs the clone at the store, since every stored bundle would otherwise be that one buffer.

### Pitfalls and edge cases

- The general trap: `append` may or may not allocate, so the result of `append(s, x)` can share memory with `s` and with every other slice appended from `s`. Never keep a slice built by `append` from a slice someone else also appends to.
- The failure depends on capacity, not on the data, so small tests and some large ones pass. Test several sizes, at least one just above a power of two.
- `copy(dst, bundle)` into a `dst` with length 0 copies nothing. Use `slices.Clone`, `append([]int(nil), bundle...)`, or `make([]int, len(bundle))` followed by `copy`.

### Prevention

- Treat a slice parameter as borrowed. Copy it before storing it in a result, a map, a struct or a channel.
- Write table tests that cover sizes on both sides of capacity boundaries, and compare the full result rather than spot-checking the last element.
- The race detector does not help here (one goroutine), and `go vet` has no check for it. A unit test that compares the whole output is the guard.

### Language notes

- Go only. In Python, Java, Kotlin and TypeScript, the usual version of this code builds a new list for every call (`bundle + [x]`, `new ArrayList<>(bundle)`, `bundle + x`, `[...bundle, x]`) or backtracks on one list and copies at the store; there is no operation that appends in place sometimes and allocates other times.
- Rust has no equivalent: a `Vec` owns its buffer, and two `Vec`s never share one. Extending a bundle for each sibling needs an explicit `clone()` or a push and pop on one `Vec`, and storing that one `Vec` in the result moves it, so the compiler forces the copy that the Go code forgot.
