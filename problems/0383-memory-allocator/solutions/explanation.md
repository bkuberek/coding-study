# Memory Allocator: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| block-list | optimal | O(b) per allocate or free; O(t b) per compare | O(b) | default answer; one list of blocks in address order serves every policy |

Here `b` is the number of blocks and `t` the length of a trace.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | A list of blocks in address order, each with its start, size and used flag; split on allocate | `blocks`, and a flag that remembers whether `allocate` was ever called |
| 2 | A coalescing switch; `free` merges with free neighbors; a report over the free blocks | `coalescing` |
| 3 | A policy switch; the choice of block moves into one function; a rover for next fit; `compare` builds fresh allocators | `policy`, `rover` |
| 4 | A fourth policy that rounds to powers of two, splits in halves and merges buddies; the requested size per block | `requested` on each block |

The early choice that keeps the later levels cheap is to model the heap as the blocks, not as bytes: a block list answers `heapMap` directly, makes the neighbors of a block its list neighbors, and lets every policy share the same split and merge code. Keeping the "was `allocate` called" flag from the start makes the configuration methods of levels 2 to 4 one line each.

## Approach: block-list (Address-ordered list of blocks with splitting, merging and buddies)

### Intuition

An allocator is bookkeeping over one invariant: the blocks cover the heap exactly, in address order. Allocation picks a free block and may cut it in two; freeing flips a flag and may glue neighbors together; every report is a pass over the list. The policies differ only in which free block they pick, so they are a single function with a switch. The buddy system is the same list with stricter cutting and gluing rules: blocks are halved instead of cut to size, and a block is glued only to its buddy, whose address is one XOR away.

### Algorithm

1. Level 1: the list starts with one free block `(0, heapSize)`. `allocate(n)` computes `need = 8 + 8 * ceil(n / 8)`, takes the first free block with `size >= need`, splits it when `size - need >= 16` (inserting the free rest after it), marks it used and returns `start + 8`. `free(a)` finds the block that starts at `a - 8`; if it exists and is used it becomes free, otherwise the answer is `"invalid"`.
2. Level 2: with coalescing on, `free` merges the block with the next one if that is free, then the previous one with it if that is free. `freeReport` sums and maximizes the sizes of the free blocks and computes `100 * (bytes - largest) div bytes`.
3. Level 3: the choice of block is one function: the first fit, the first fit at or after the block at the rover and then from the start (next fit), or the smallest fit with the lowest address on ties (best fit). After an allocation the rover is the end of the used block, modulo the heap size; when a merge swallows the block at the rover, the rover moves to the start of the merged block. `compare` builds three allocators with the same heap size and coalescing setting, replays the trace on each, remembering every returned address in a list so that `-k` frees the `k`-th one, and reports the failures and `freeReport()`.
4. Level 4: in buddy mode, `need` is the smallest power of two that is at least `n + 8` and 16; the chosen block is the smallest free one that fits, lowest address first, and it is halved until it has the needed size, each upper half becoming a free block. `free` then loops: the buddy of the block at `a` with size `s` is at `a XOR s`; if a free block of size `s` starts there, the two merge into the block at `min(a, a XOR s)` with size `2s`. Every allocate records the request size, and `wasted` sums `size - 8 - requested` over the used blocks.

### Correctness

Invariant: after every call the blocks are disjoint, sorted by start, and cover `[0, heapSize)`. A split replaces one block by two that cover the same bytes; a merge replaces two adjacent blocks by one that covers the same bytes. With coalescing on, every `free` restores the second invariant "no two free blocks are adjacent": before the call it held, so the only free neighbors that can appear are those of the freed block, and both are merged.

Rover: the rover is always the start of a block. It is set to the end of a used block, which is the start of the next block (or 0 at the end of the heap). A split never moves block starts that already exist, and a merge removes exactly one start, the start of the second block, which is why the rover moves to the merged block when it pointed at the second one.

Buddies: by induction, every block of size `s` starts at a multiple of `s`, since the whole heap starts at 0 and halving a block aligned to `s` gives two blocks aligned to `s / 2`. So the two halves of a block of size `2s` at `a` are at `a` and `a + s`, where `a` is a multiple of `2s`, and each one's buddy is the other: `a XOR s = a + s` and `(a + s) XOR s = a`. A block at the buddy address with the same size is exactly that other half, whole; if it is smaller, the other half is split and cannot be merged, which the size test detects.

### Complexity

- Time: O(b) per allocate or free; O(t b) per compare — choosing a block, finding the block at an address and inserting or removing a block in a list are each a pass over at most `b` blocks; a buddy split or merge loop runs at most `log2(heapSize)` times; `compare` replays the trace three times.
- Space: O(b) — one record per block, and the returned addresses of a trace in `compare`.

### Trade-offs

- A list makes every call linear in the number of blocks, which is fine here. Real allocators index free blocks by size (segregated free lists or trees) so that best fit costs a lookup, and find a block's neighbors from its header and its predecessor's footer, which is what boundary tags give: O(1) merging without any search.
- First fit is simple and, with blocks kept in address order, wastes little; next fit spreads allocations around the heap and, in the studies surveyed by Wilson and colleagues, fragments more; best fit wastes little but needs an index to be fast.
- The buddy system finds a buddy with one XOR and needs no footer, but rounds every request up to a power of two: up to almost half of a block can be wasted, which `wasted` makes visible.
- Coalescing on every `free` keeps fragmentation low but costs time on every call; deferred coalescing keeps freed blocks of popular sizes for quick reuse and merges later.

### Pitfalls and edge cases

- The block size includes the 8-byte header and is rounded up to a multiple of 8: 1 byte needs 16, 8 bytes 16, 9 bytes 24, 17 bytes 32.
- Split only when the leftover is at least 16 bytes, the smallest block; a leftover of exactly 16 is split, one of 8 is not, and is wasted inside the used block.
- `free` takes the payload address: only `start + 8` of a used block is valid. An address inside a block, the start of a block (its header), a free block, a negative address or one past the heap is `"invalid"`.
- At level 1 free blocks are never merged, even side by side, and `setCoalescing` and `setPolicy` refuse to change anything once `allocate` was called, failed calls included.
- With coalescing, a freed block between two free ones merges with both.
- The fragmentation is `100 * (bytes - largest) / bytes` rounded down, and 0 when nothing is free.
- Next fit wraps around to the start; its rover follows a merge; a failed request does not move it.
- Best fit breaks ties by the lowest address. Policy names are exact: `Best-Fit` is unknown, and an unknown name is reported before a late change.
- `compare` must not touch this allocator, uses its coalescing setting, counts `-k` from 1 and skips the frees of failed requests.
- Buddies: count the header before rounding (121 bytes need 256, not 128); keep the lower half of each split; take the smallest free block, not the first; merge repeatedly, but never two free blocks that are not buddies, whatever the coalescing setting.
- `wasted` counts used blocks only and covers every policy, including the leftovers that first fit hands out unsplit.

### Language notes

- The blocks are a Python list of small objects, a TypeScript array of objects, a Java `ArrayList` of a small class, a Kotlin `MutableList` of a class, a Go slice of structs and a Rust `Vec` of structs; inserting and removing in the middle is linear in all of them, which the constraints allow.
- Go slices of structs are values: update a block through its index (`a.blocks[i].used = true`), not through a copy from `range`. Rust does the same with `self.blocks[i]`.
- `compare` creates new allocators of the same class: Python and TypeScript call the constructor, Java and Kotlin `new MemoryAllocator(...)` and `MemoryAllocator(...)`, Go `NewMemoryAllocator`, Rust `MemoryAllocator::new`.
- `compare` returns `list<list<int>>`: `List<List<Integer>>` in Java, `List<List<Int>>` in Kotlin, `[][]int` in Go and `Vec<Vec<i32>>` in Rust.
- The address arithmetic stays far below 2^31, so `int` is enough everywhere; XOR is `^` in every language except Kotlin, where it is `xor`.

## Further reading

- P. R. Wilson, M. S. Johnstone, M. Neely and D. Boles, "Dynamic storage allocation: a survey and critical review", Memory Management (IWMM 1995), Lecture Notes in Computer Science, Springer, 1–116, 1995, [doi:10.1007/3-540-60368-9_19](https://doi.org/10.1007/3-540-60368-9_19): internal and external fragmentation (section 2.1); splitting and coalescing; first fit, next fit with a roving pointer, and best fit, with the finding that next fit has caused more fragmentation than best fit or address-ordered first fit in several studies (section 3.4); boundary tags with a header and a footer, credited to Knuth, and the optimization that keeps the footer only in free blocks (section 3.2); buddy systems, the buddy found by address computation, binary buddies with power-of-two sizes, and an expected internal fragmentation of very roughly 28% (section 3.7); and a history in which Knowlton's 1965 paper is the first on the binary buddy system and Knuth's book introduces next fit and boundary tags.
- D. E. Knuth, The Art of Computer Programming, Volume 1: Fundamental Algorithms, 3rd edition, Addison-Wesley, 1997, the section "Dynamic Storage Allocation" ([publisher page](https://www.informit.com/store/art-of-computer-programming-volume-1-fundamental-algorithms-9780133489330)): the book that the survey, citing its 1973 second edition, credits with next fit, boundary tags and splitting thresholds.
- K. C. Knowlton, "A fast storage allocator", Communications of the ACM 8(10), 623–624, 1965, [doi:10.1145/365628.365655](https://doi.org/10.1145/365628.365655): the binary buddy system.
