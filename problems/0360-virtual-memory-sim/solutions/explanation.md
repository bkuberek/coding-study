# Virtual Memory Sim: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| page-map | optimal | O(t + f) per translation, t the TLB entries and f the frames; O(m) per tableBytes over m pages in the table; O(w log w) per workingSet over w references | O(m + t + f + r) for r references | default answer; one translation path serves all four levels, and each level adds a piece of state beside it |

Here `m` is the number of pages in the page table, `t` the TLB's entries, `f` the frames, `r` the references since the run began and `w` the window asked for.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | A page table and a fault count | the page size and its bit count; a map from page to frame; the faults |
| 2 | A TLB in front of the page table | a map from page to frame kept in order of use, its size, the hits and the misses |
| 3 | Demand paging with three policies | the frame count and policy; per frame, its page and its use bit; the order in which pages were loaded and last used; the clock hand |
| 4 | Table sizes and the working set | the list of pages referenced since the run began |

The early choice that keeps the later levels small is to send every translation through one private method that does the TLB lookup, the page table lookup and the fault, in that order. Level 2 adds a branch at its start, level 3 adds a load at the point where level 1 returned `-1`, and level 4 adds one line that records the reference. A second choice is to invalidate the TLB in the methods that change the page table, at level 2: level 3 then gets correct eviction for free by calling the same invalidation for the victim.

## Approach: page-map (A page map, a TLB in use order and a frame table)

### Intuition

Translation is two lookups and some arithmetic: find the frame of the page, then put the offset back. The TLB is a cache in front of the first lookup, so it must give the same answer as the page table at every moment, which is why any change to a mapping removes the page's entry. Demand paging fills in the one case where the page table has no answer: instead of failing, it makes room and records a new mapping, and the rest of the translation does not change. Each policy is a different answer to "which resident page is least worth keeping", and each needs just the state that answers it: when pages were loaded, when they were last used, or one bit per frame and a position.

### Algorithm

1. Level 1: with `pageSize = 2^k`, `split(a)` is `[a >> k, a & (pageSize - 1)]`. `mapPage` and `unmapPage` change the map and return whether the page was new, or present. `translate` splits the address, finds the frame, and returns `frame * pageSize + offset`, or counts a fault and returns `-1`.
2. Level 2: with a TLB, look the page up there first. A hit counts, moves the entry to the most recent end, and gives the frame. A miss counts and falls through to the page table; when the page is found, add it at the most recent end, after removing the least recent entry if the TLB is full. `mapPage` and `unmapPage` delete the page's entry; `flushTlb` clears all entries; `enableTlb` starts an empty TLB and zero counts.
3. Level 3: `useFrames` resets the page table, the TLB's entries, the counts, the frames and the history. On a fault, take the next free frame (frames fill in order and are never freed), or ask the policy for a victim frame; remove the victim's page from the page table, from the TLB and from the load and use orders; then put the page in the frame. After the page is found or loaded, record the use: move it to the recent end of the use order and set its frame's use bit. FIFO's victim is the oldest page in the load order, LRU's the oldest in the use order. The clock clears and skips frames whose bit is set, takes the first frame whose bit is clear, and leaves the hand one past it.
4. Level 4: `walk` splits the page number again by `E = pageSize / entryBytes`. `tableBytes` counts `2^(addressBits - k)` entries for one level, and for two levels the directory's `2^(addressBits - k) / E` entries plus one page for each distinct `page / E` in the page table. Every translation appends its page to the history; `workingSet` takes the set of the last `window` entries and sorts it, and `thrashing` compares its size with the frames once demand paging is on.

### Correctness

The TLB invariant: every entry `(page, frame)` in the TLB is also in the page table. It holds when the TLB is created empty; a miss adds an entry it has just read from the page table; `mapPage`, `unmapPage`, `useFrames` and an eviction delete the entries of the pages they change, before anything else can read them. So a hit gives exactly what the page table would, and the TLB only changes how fast, and how the hits and misses are counted.

The order of use is a list in which every resident page appears once, moved to the end on each use, so its front is the least recently used page; the load order is the same list moved only on load. The victim is removed from both lists, from the page table and from the TLB at once, so no stale state is left for the page that takes its frame.

The clock terminates: in one turn around the circle, every bit it passes is cleared, so it stops by the time it comes back to its starting frame. It evicts a page with a clear bit, which has not been used since the hand last passed it, and so it gives each recently used page a second chance before it can be evicted.

The table sizes follow from the definitions: an inner table covers `E` consecutive pages, so a page is in inner table `page / E`, and the number of inner tables needed is the number of distinct values of `page / E`. The working set is, by definition, the set of pages in the last `window` references, and the history holds every reference of the run in order.

### Complexity

- Time: O(t + f) per translation, t the TLB entries and f the frames; O(m) per tableBytes over m pages in the table; O(w log w) per workingSet over w references — with ordered maps (Python, TypeScript, Java and Kotlin), a TLB hit, a miss, a FIFO or LRU eviction and a use are O(1), and only the clock's sweep is O(f); Go and Rust keep timestamps and scan the at most 64 entries, which is the O(t + f). `tableBytes` builds a set of table numbers; `workingSet` builds a set of up to `w` pages and sorts it.
- Space: O(m + t + f + r) for r references — the page table, the TLB, the per-frame state, and the history of references, which grows by one for each translation in a run.

### Trade-offs

- Exact LRU needs work on every memory access, which hardware cannot afford for page replacement; the clock needs only a bit that the hardware sets, and does its work at fault time. It cannot tell apart pages that were all used since the last sweep, and when every bit is set it degrades to FIFO for that eviction.
- FIFO is the simplest and suffers from Belady's anomaly; LRU has the stack property, so its faults never rise with more frames, but its bookkeeping is the most expensive.
- Keeping the whole history makes `workingSet` exact for any window, at O(r) memory. A system that knows its window keeps a fixed-size ring of the last `w` references and a count per page, so that the size of the working set is updated in O(1) per reference.
- A two-level table saves memory when the address space is sparse and costs a second memory access on every TLB miss. With a dense address space it costs more than one level, because of the directory.

### Pitfalls and edge cases

- Addresses reach 2^48: 32-bit integers overflow in Java, Kotlin, Go and Rust if the address or `frame * pageSize` is computed in `int`. TypeScript numbers are exact up to 2^53, and every value here fits; use arithmetic, not 32-bit bitwise operators, on addresses in TypeScript.
- `mapPage` replaces an existing mapping and returns `false`; it does not refuse the change.
- A remapped or unmapped page must leave the TLB, or the next hit gives the old frame. An evicted page must leave it too.
- A fault is also a TLB miss, and adds nothing to the TLB.
- When the victim is in a full TLB, remove its entry before adding the new page: the removal makes room, and adding first would evict another entry.
- A TLB hit is a use of the page: LRU and the clock must see it, not only the translations that read the page table.
- The clock's hand starts at frame 0, does not move while free frames are filled, and stops one past the frame it fills.
- `useFrames` resets the counts and the history, and empties the TLB without turning it off.
- The directory takes exactly its entries' bytes, not a whole page.
- `thrashing` needs strictly more pages than frames, and is `false` before `useFrames`.

### Language notes

- The TLB and the two orders are ordered collections: Python's `OrderedDict` (`move_to_end`, `popitem(last=False)`); TypeScript's `Map` and `Set`, which iterate in insertion order (delete and add again to move a key to the end); and in Java and Kotlin a `LinkedHashMap` in access order for the TLB, whose `get` moves an entry to the end, and `LinkedHashSet`s for the orders. Go has no ordered map, and Rust's standard library has none either: both keep a counter that grows with each reference, store the counter of the last use or the load with each entry, and scan for the smallest when evicting, which is fine for at most 64 entries.
- Addresses, pages and frames are `long`: `Long` in Kotlin, `int64` in Go, `i64` in Rust, and a `number` in TypeScript, where they stay below 2^53.
- `split`, `walk`, `tableBytes`, `resident` and `workingSet` return `long[]`: `long[]` in Java, `LongArray` in Kotlin, `[]int64` in Go and `Vec<i64>` in Rust.
- The page size's bit count is `bit_length() - 1` in Python, `Integer.numberOfTrailingZeros` in Java and Kotlin, `bits.TrailingZeros` in Go and `trailing_zeros` in Rust; TypeScript divides with `Math.floor` instead of shifting.

## Further reading

- R. H. Arpaci-Dusseau and A. C. Arpaci-Dusseau, [Operating Systems: Three Easy Pieces](https://pages.cs.wisc.edu/~remzi/OSTEP/), version 1.10, free online:
  - [Paging: Introduction](https://pages.cs.wisc.edu/~remzi/OSTEP/vm-paging.pdf): virtual page numbers, offsets, frames, page tables, and the size of a linear table for a 32-bit address space with 4 KB pages.
  - [Paging: Faster Translations (TLBs)](https://pages.cs.wisc.edu/~remzi/OSTEP/vm-tlbs.pdf): hits and misses, locality, flushing on a context switch and address-space identifiers, and LRU replacement and its weak spot on a loop one page larger than the TLB.
  - [Paging: Smaller Tables](https://pages.cs.wisc.edu/~remzi/OSTEP/vm-smalltables.pdf): multi-level page tables, the page directory, and why a large address space needs more than two levels.
  - [Beyond Physical Memory: Policies](https://pages.cs.wisc.edu/~remzi/OSTEP/vm-beyondphys-policy.pdf): the optimal policy, FIFO, LRU, Belady's anomaly and the stack property, the use bit and the clock algorithm, and thrashing.
- L. A. Belady, "A study of replacement algorithms for a virtual-storage computer", IBM Systems Journal 5(2), 1966, [doi:10.1147/sj.52.0078](https://doi.org/10.1147/sj.52.0078): the optimal replacement policy.
- L. A. Belady, R. A. Nelson and G. S. Shedler, "An anomaly in space-time characteristics of certain programs running in a paging machine", Communications of the ACM 12(6), 1969, [doi:10.1145/363011.363155](https://doi.org/10.1145/363011.363155): the anomaly of FIFO.
- R. L. Mattson, J. Gecsei, D. R. Slutz and I. L. Traiger, "Evaluation techniques for storage hierarchies", IBM Systems Journal 9(2), 1970, [doi:10.1147/sj.92.0078](https://doi.org/10.1147/sj.92.0078): the paper the textbook above cites for the stack property, which LRU has and FIFO lacks.
- P. J. Denning, "The working set model for program behavior", Communications of the ACM 11(5), 1968, [doi:10.1145/363095.363141](https://doi.org/10.1145/363095.363141): the working set model, in which a process's working set is the collection of its most recently used pages.
- P. J. Denning, "Thrashing: its causes and prevention", Proceedings of the AFIPS Fall Joint Computer Conference, 1968, [doi:10.1145/1476589.1476705](https://doi.org/10.1145/1476589.1476705): the working set `W(t, τ)` restated as the pages a process referenced in the virtual-time interval `(t - τ, t)`, thrashing, and the working-set policy under which a process is active only when its working set is in main memory.
- The Linux kernel documentation, [Cache and TLB Flushing Under Linux](https://docs.kernel.org/core-api/cachetlb.html): the kernel flushes TLB entries after it changes page tables, because stale translations may otherwise remain; and [5-level paging](https://docs.kernel.org/arch/x86/x86_64/5level-paging.html): four-level paging limited x86-64 to 256 TiB of virtual address space.
