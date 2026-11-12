# Memory Allocator

## Statement

Build `MemoryAllocator`, the part of a language runtime or an operating system that hands out memory: when a program asks for 24 bytes, the allocator finds 24 free bytes in a large region of memory, the *heap*, and returns their address; when the program frees them, the allocator takes them back for later requests. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**What an allocator does with free memory.** The heap is one long run of bytes. The allocator divides it into *blocks*, each either *used* (handed out and not yet freed) or *free*. A request is served from a free block, splitting it when it is larger than needed. Over time, used and free blocks alternate, and the free memory ends up in many small pieces. Then a request can fail although enough bytes are free in total, because no single free block is large enough: this is *external fragmentation*. Bytes handed out with a block but never asked for, such as padding, are *internal fragmentation*. Every allocator design is a trade between speed and these two kinds of waste.

For example, in a heap of 64 bytes, three blocks of 16 bytes are used and the last 16 bytes are free. The program frees the first two blocks. 48 bytes are now free, but in three pieces of 16, so a request that needs a block of 32 bytes fails: unless the allocator merges the two free blocks that sit side by side (level 2).

Level 1 builds the simplest allocator, *first fit*. Level 2 merges free neighbors with *boundary tags*. Level 3 compares three ways of choosing a free block, and level 4 builds a *buddy* allocator, which trades internal fragmentation for very fast merging.

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 40, level 2 by 60, level 3 by 90 and level 4 by 115, keeping the last minutes for a final run.

## Input

- `MemoryAllocator(heapSize)`: creates an allocator over a heap of `heapSize` bytes, at addresses `0` to `heapSize - 1`. `heapSize` is a multiple of 8, from 16 to 2^20.
- A request size is from 1 to 10^6 bytes, and an address passed to `free` is any integer from -10^6 to 10^6.
- Each level's section describes the methods it adds and their parameters.

## Output

`allocate` returns an address, or `-1` when it cannot serve the request, in which case the heap does not change. Methods that change the allocator's state or its settings return a *status*, a string: `"ok"`, or one of the words the level lists, in which case **nothing has changed**. Reports return lists, described by each level.

## Level 1: First fit over a fixed heap

**Blocks.** The blocks cover the heap exactly, in address order, without gaps. At the start there is one free block, the whole heap.

- Each block begins with a **header** of 8 bytes, where a real allocator stores the block's size and whether it is used. The bytes after the header are the *payload*: what the program gets. The address that `allocate` returns is the payload's, the block's start plus 8.
- Every block starts at a multiple of 8 and its size, header included, is a multiple of 8, so every returned address is a multiple of 8 (it is *aligned*). A request for `n` bytes therefore needs a block of `8 + n` rounded up to a multiple of 8: `need = 8 + 8 * ceil(n / 8)`. A request for 1 byte needs 16 bytes, one for 8 bytes also 16, and one for 9 bytes 24.
- The smallest block is 16 bytes: a header and 8 bytes of payload.

**First fit.** To serve a request, walk the blocks from address 0 and take the **first** free block whose size is at least `need`. If there is none, the request fails with `-1`. If the block is larger than `need` by **16 bytes or more**, *split* it: its first `need` bytes become the used block, and the rest becomes a new free block right after it. Otherwise the whole block is used, and the extra bytes are wasted inside it.

**Freeing.** Freeing a block marks it free. At this level, free blocks are never merged: two free blocks side by side stay two blocks.

- `allocate(size)`: serves a request for `size` bytes and returns the address of its payload, or `-1`.
- `free(address)`: frees the used block whose payload starts at `address`. Statuses: `"invalid"` when no used block's payload starts there: the address never came from `allocate`, points inside a block, or belongs to a block that is already free.
- `heapMap()`: the blocks in address order, one line each: `"<start> <size> used"` or `"<start> <size> free"`, with the block's start and its size, header included.

### Example 1

<!-- case: ex1 -->

A heap of 128 bytes. A request for 10 bytes needs `8 + 16 = 24` bytes; the first block is split, and the payload starts at 8. A request for 1 byte needs 16 bytes, at 24, so its address is 32; one for 20 bytes needs 32 bytes, at 40. Freeing 32 leaves a free block of 16 bytes between two used ones. Freeing it again is `"invalid"`. The next request for 8 bytes needs 16 bytes, and first fit finds the free block at 24 before the large one at the end.

### Example 2

<!-- case: ex2 -->

A heap of 64 bytes. 40 bytes need a block of 48, which leaves exactly 16 bytes, enough to split. After a request for 1 byte takes them, the heap is full. Once the first block is freed, a request for 30 bytes needs 40, and the free block of 48 is only 8 bytes larger: too little to split, so the whole block is used. 9 is inside a block, and 100 is outside the heap.

## Level 2: Coalescing with boundary tags

**Coalescing.** An allocator that never merges free blocks breaks its heap into ever smaller pieces. *Coalescing* merges a freed block with the free blocks right before and right after it, so that free memory stays in as few pieces as possible.

**Boundary tags.** Finding the block right after a block is easy: it starts where this one ends. Finding the block right before it is not, since blocks have different sizes. Knuth's *boundary tag* technique stores the size of a block at both of its ends, in its header and in a *footer*: the footer of the previous block sits just before this block's header, so freeing a block can look at both of its neighbors in constant time and merge with each one that is free. A later refinement, which Wilson and colleagues credit to Standish (1980): only free blocks need the footer, because for a used block a bit saying that it is in use is enough, and it can be kept in the next block's header. The footer then fits in the free block's unused payload, so the sizes of the blocks do not change. You may keep the blocks in any structure you like: the problem checks the blocks and the reports, not the bytes.

- `setCoalescing(enabled)`: turns coalescing on (`true`) or off (`false`); it is off by default, which is the behavior of level 1. The setting is chosen before the heap is used. Statuses: `"too-late"` when `allocate` has already been called on this allocator.
- With coalescing on, `free` marks the block free, then merges it with the next block if that one is free, and with the previous block if that one is free, into one free block. After every `free` no two free blocks are neighbors.
- `freeReport()`: four numbers about the free blocks: `[count, bytes, largest, fragmentation]`. `count` is the number of free blocks, `bytes` the sum of their sizes (headers included), `largest` the size of the largest one, and `fragmentation` the share of free bytes that lie outside the largest free block, in whole percent rounded down: `100 * (bytes - largest) / bytes` with integer division, and `0` when no byte is free. A fragmentation of 0 means that all free memory is one block.

### Example 1

<!-- case: ex3 -->

The heap of the statement's example, with coalescing on. Freeing the block at 0 leaves it alone, since its neighbor is used; freeing the block at 16 merges it with the free block at 0. The free memory is now a block of 32 and the block of 16 at the end: 48 bytes, of which 16 lie outside the largest block, so the fragmentation is 33. The request for 20 bytes needs 32 and fits in the merged block. Turning coalescing off after that is too late.

### Example 2

<!-- case: ex4 -->

The same requests with coalescing off: three free blocks of 16, with 32 of the 48 free bytes outside the largest one (66%), and the request that needs 32 bytes fails.

## Level 3: Placement policies

Which free block a request should take is the allocator's *placement policy*, and it matters more for fragmentation than it seems. Classic studies, surveyed by Wilson and colleagues in 1995, found that *best fit* and first fit with the blocks in address order usually waste little memory, and that *next fit* tends to fragment more.

| Policy | Takes |
|--------|-------|
| `first-fit` | the first free block, from address 0, that is large enough (level 1) |
| `next-fit` | the first free block that is large enough, searching from where the last allocation ended and wrapping around |
| `best-fit` | the smallest free block that is large enough; among several of the same size, the one at the lowest address |

**Next fit** keeps a *rover*: the start of the block where its next search begins. The rover starts at 0. A search looks at the blocks in address order from the block at the rover to the last block, then from the first block up to the block before the rover's block, and takes the first free block that is large enough. After an allocation, the rover is the start of the block right after the used block (the free rest of a split block, if there is one), or 0 when the used block ends the heap. A failed request does not move it. When coalescing merges the block at the rover into the block before it, the rover moves to the start of the merged block.

Splitting works the same for every policy: the used block is the first `need` bytes of the chosen block.

- `setPolicy(policy)`: chooses the policy; `first-fit` is the default. Statuses, in this order: `"unknown-policy"` when `policy` is not one of the names in the table (spelled exactly); `"too-late"` when `allocate` has already been called.
- `compare(trace)`: replays a list of requests on three new allocators with this allocator's heap size and coalescing setting, one per policy, in the order `first-fit`, `next-fit`, `best-fit`, and returns one row per policy: the number of requests that failed, followed by the four numbers of `freeReport()` at the end of the trace. In the trace, a positive number `n` is a request for `n` bytes, and `-k` frees the address returned by the `k`-th request of the trace (counting the requests from 1); when that request failed, `-k` does nothing. This allocator itself does not change.

### Example 1

<!-- case: ex5 -->

With next fit, the third request ends at 48, so the rover is 48. The block at 0 is then freed, but the next search starts at 48 and takes the block there; first fit would have reused the block at 0. A policy can be chosen only before the first request, and `worst-fit` is not one of the three names.

### Example 2

<!-- case: ex6 -->

In the first trace, freeing the first and the third request leaves two holes of 48 bytes. First fit puts the request for 24 bytes (a block of 32) in the first hole and then the one for 32 bytes (40) in the second, leaving two pieces. Next fit and best fit put the first of them at the end of the heap, where exactly 32 bytes are free, and the second in the first hole, so they end with one free block of 48. In the second trace, next fit skips the hole at 0 and keeps carving the end of the heap, so it ends with two free blocks where the others have one.

## Level 4: The buddy allocator

The *buddy system*, whose first paper Knowlton published in 1965, makes merging almost free by restricting the sizes of blocks:

- The heap size is a power of two, and every block size is a power of two, at least 16. A block of size `s` starts at a multiple of `s`.
- A request for `n` bytes needs the smallest power of two that is at least `n + 8` and at least 16.
- To serve it, take the **smallest** free block that is large enough, the one at the lowest address among several of that size. While the block is larger than needed, split it into two halves: the lower half goes on being split or is used, and the upper half becomes a free block. The two halves of a split are *buddies*.
- When a block is freed, it merges with its buddy if the buddy is a whole free block of the same size, into the block they were split from; the merged block then tries to merge with its own buddy, and so on, up to the whole heap. The buddy of the block of size `s` at address `a` is at address `a XOR s` (the bit for `s` flipped), so finding it needs no search and no footer.

Rounding every request up to a power of two wastes memory inside the blocks: Wilson and colleagues cite an expected internal fragmentation of very roughly 28% for binary buddies.

- `setPolicy("buddy")`: a fourth policy. One more status, after the other two: `"bad-size"` when the heap size is not a power of two. The coalescing setting has no effect on the buddy policy, which always merges buddies and never merges two free blocks that are not buddies.
- `wasted()`: the bytes inside used blocks that the program did not ask for, under any policy: the sum, over the used blocks, of the block's size minus 8 minus the size of its request. It counts the alignment padding, the extra bytes of a block that was too small to split and, with buddies, the rounding to a power of two.
- `compare` still replays its trace with the three policies of level 3.

### Example 1

<!-- case: ex7 -->

10 bytes need a block of 32 (18 rounded up to a power of two). The heap of 128 is split into two blocks of 64, the lower one into two of 32, and the lower 32 is used: 14 of its bytes are wasted. 40 bytes need 64, which the free block at 64 provides whole. Freeing the block at 0 merges it with its buddy at 32 into a block of 64; that block's buddy, at 64, is used, so the merging stops there.

### Example 2

<!-- case: ex8 -->

96 is not a power of two, so the heap cannot use buddies and stays first fit, where a request for 1 byte wastes 7 bytes and one for 20 bytes wastes 4. The policy cannot change once the heap is in use.

## Constraints

- At most 2000 calls per test, and at most 2000 entries in a trace.
- Every entry of a trace is a request size from 1 to 10^6 or a `-k` whose `k`-th request comes earlier in the trace, and each request is freed at most once.
- At most a few thousand blocks exist at a time, so walking the list of blocks for each call is fast enough.

## Follow-ups

- First fit walks every block from the start. How would a free list ordered by address, or a balanced tree of free blocks keyed by address, make the search faster without changing which block it picks?
- Best fit keyed by size can be served by a tree or by *segregated free lists*, one per size class. What changes when the classes are ranges of sizes rather than exact sizes?
- Merging every free block at once costs time on every `free`. When can *deferred coalescing* (keeping freed blocks of popular sizes aside for reuse) pay off, and what does it cost in fragmentation?
- The buddy allocator wastes memory to round sizes up. How would sizes that are not powers of two, such as a Fibonacci series, reduce it, and what makes finding a buddy harder then?
- Real heaps can grow: when no block fits, the allocator asks the operating system for more memory at the end. How would `allocate` change, and which block would a new region merge with?

## Hints

### Hint 1

You never need an array of bytes: every method asks about blocks, not about what the bytes hold. Keep the blocks in a list ordered by address, each with its start, its size and whether it is used; at the start the list holds one free block, the whole heap. Splitting a block inserts one new block right after it, and the payload address of a block is its start plus 8, so `free` looks for the block that starts at `address - 8`.

### Hint 2

Compute the size a request needs once, in one place, and test it on sizes 1, 8, 9, 16 and 17. Split only when the leftover is at least 16 bytes; otherwise hand out the whole block.

### Hint 3

For coalescing, after marking the block free, look at its neighbors in the list: merge with the next one first, then with the previous one. Each merge removes one block from the list and adds its size to the block before it.

### Hint 4

For `freeReport`, collect the sizes of the free blocks in one pass. Use integer arithmetic for the fragmentation, and test the case with no free byte at all.

### Hint 5

Write one function that picks a block for a request and switch on the policy inside it. For next fit, find the position of the block that starts at the rover, look at the blocks from there to the end, then from the start. Update the rover after a successful allocation, and when a merge swallows the block it points at.

### Hint 6

`compare` is three fresh allocators run on the same trace: keep the address each request returned, in order, so that `-k` can free the `k`-th one, and skip the ones that failed.

### Hint 7

For buddies, splitting is a loop that halves the chosen block until it has the needed size, keeping the lower half. Freeing is a loop too: compute the buddy's address with XOR, look for a free block of the same size there, merge, and repeat with the merged block until there is no such buddy or the block is the whole heap. For `wasted`, store the size of its request with each used block when you hand it out.
