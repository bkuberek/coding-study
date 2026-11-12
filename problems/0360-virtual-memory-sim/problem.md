# Virtual Memory Sim

## Statement

Build `VirtualMemory`, a simulator of how an operating system and a processor turn the addresses a program uses into places in the computer's memory. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working.

**What is virtual memory?** Every program sees memory as one long row of bytes numbered from 0, its own private *address space*. The numbers it uses are *virtual addresses*. The real memory chips (RAM) are shared by every running program, and their bytes have *physical addresses*. On every memory access, the hardware *translates* the virtual address into a physical one, using tables the operating system keeps. This is what keeps programs apart, since none can name another's memory, and what lets the system keep part of a program on disk when RAM runs short.

**Pages and frames.** Translating byte by byte would need a table as large as memory. Instead, memory is cut into blocks of the same size, the **page size**, a power of two such as 4096. A block of the address space is a **page**, a block of physical memory a **frame**, and both are numbered from 0. Byte `b` of a page is translated to byte `b` of the frame that holds the page: the position inside the block, the **offset**, never changes.

**The page table** maps page numbers to frame numbers. To translate an address: split it into the page number (`address / pageSize`, rounded down) and the offset (`address % pageSize`), look the page up, and put the offset back on the frame: `frame * pageSize + offset`. A page with no frame cannot be translated: the access is a **page fault**, and the operating system has to step in.

**A worked example, by hand.** With 32-byte pages, the address 100 is 3 * 32 + 4: page 3, offset 4. If page 3 is held by frame 5, the physical address is 5 * 32 + 4 = 164. In binary, 32 is 2^5, so the offset is the lowest 5 bits of the address, and the page number is the bits above them:

| | Binary | Decimal |
|---|---|---|
| virtual address | `11` `00100` | 100 |
| page number, offset | `11`, `00100` | 3, 4 |
| frame number, offset | `101`, `00100` | 5, 4 |
| physical address | `101` `00100` | 164 |

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 30, level 2 by 55, level 3 by 90 and level 4 by 115, keeping the last minutes for a final run.

## Input

- `VirtualMemory(pageSize)`: creates an empty address space whose page size is `pageSize` bytes, a power of two from 2 to 65536.
- Addresses, page numbers and frame numbers are non-negative integers; an address is below 2^48.
- Each level's section describes the methods it adds and their parameters.

## Output

Translations return a physical address, or `-1` when the page has no frame. Counts are integers that start at 0. Lists of pages are sorted in increasing order, with each page once.

## Level 1: Pages and the page table

- `split(address)`: the page number and the offset of `address`, as `[page, offset]`.
- `mapPage(page, frame)`: maps the page `page` to the frame `frame`. It returns `true` when the page had no frame before, and `false` when the call replaces an earlier mapping; either way the page now maps to `frame`. Several pages may map to the same frame.
- `unmapPage(page)`: removes the mapping of `page`. It returns `true` when the page had one, and `false` otherwise.
- `translate(address)`: the physical address of `address`, or `-1` when its page is not mapped. Each translation that finds no frame is one **page fault**.
- `faults()`: the number of page faults so far.

Because the page size is a power of two, splitting an address needs no division: with `pageSize = 2^k`, the page number is the address shifted right by `k` bits, and the offset is the address with every bit above the lowest `k` cleared. Addresses here reach 2^48, past 32 bits, so they need 64-bit integers.

### Example 1

<!-- case: ex1 -->

The worked example: address 100 is page 3, offset 4, and with page 3 in frame 5 it becomes 164. Address 70 is page 2, offset 6; page 2 has no frame yet, so the first translation faults and returns `-1`. Once page 2 is mapped to frame 0, address 70 becomes 6. Addresses 96 and 127 are the first and the last byte of page 3.

### Example 2

<!-- case: ex2 -->

With 4096-byte pages, 74565 = 18 * 4096 + 837. Mapping page 18 again replaces its frame, so `mapPage` returns `false` and the same address now lands in frame 9. Unmapping it twice returns `true`, then `false`, and the translation faults.

## Level 2: The TLB

The page table lives in memory, so a translation that reads it costs an extra memory access on top of the one the program asked for. Processors keep a small cache of recent translations, the **translation lookaside buffer** (TLB). Programs tend to use the same pages again and again (*locality*), so most translations are found in the TLB.

- `enableTlb(entries)`: from now on, every translation first looks in a TLB that holds at most `entries` translations. The TLB starts empty, and the hit and miss counts start again from 0. Calling it again replaces the TLB with a new, empty one.
- With a TLB, `translate(address)` works like this:
  - If the page is in the TLB, that is a **hit**: the translation uses the frame stored in the TLB, and the entry becomes the most recently used.
  - Otherwise it is a **miss**, and the page table is read. If the page is mapped, its translation is added to the TLB as the most recently used entry; when the TLB is full, the **least recently used** entry is removed first. If the page is not mapped, the translation is a page fault and nothing is added.
  - Every translation is exactly one hit or one miss.
- `mapPage` and `unmapPage` remove the page's entry from the TLB, if it has one, so that the TLB never gives a frame that the page table no longer says. This changes no count.
- `flushTlb()`: removes every entry from the TLB, and leaves the counts as they are. Without a TLB, it does nothing.
- `tlbHits()` and `tlbMisses()`: the hits and misses since the TLB was enabled; `0` when no TLB is enabled.

**Why least recently used?** An entry used a moment ago is likely to be used again soon, so evicting the one unused for the longest is a good guess. It has a weak spot: a loop over one page more than the TLB holds misses on every translation, because each entry is evicted just before it is needed again. Real systems also flush the TLB when they switch from one program to another, because the same virtual page means a different frame in another address space, or they tag each entry with the address space it belongs to.

### Example 1

<!-- case: ex3 -->

A TLB of 2 entries. Address 5 (page 0) misses and is added; 17 (page 1) misses and is added; 3 (page 0) hits. 40 is on page 2: the TLB is full, so page 1, the least recently used, is removed. 18 (page 1) then misses and pushes out page 0, and 7 (page 0) misses too: one hit, five misses.

### Example 2

<!-- case: ex4 -->

Remapping page 1 removes its TLB entry, so the next translation of address 17 misses and finds the new frame 2 instead of the stale frame 4. Address 33 is on page 2, which is not mapped: each try is a miss and a fault, and adds nothing to the TLB. After a flush, page 0 misses again, and the counts carry on.

## Level 3: Page replacement

So far every page was mapped by hand. With **demand paging**, the operating system loads a page into memory the first time it is used, and when every frame is taken it must choose a **victim**: a page to remove so that its frame can be reused. The choice is the *replacement policy*, and a poor choice means more page faults, each of which costs a slow read from disk.

- `useFrames(count, policy)`: switches to demand paging with `count` frames, numbered from 0, and the replacement policy `policy`, one of `"fifo"`, `"lru"` and `"clock"`. It starts a new run: the page table and the TLB are emptied (the TLB stays on with its size, if one is enabled), and the fault, hit and miss counts are reset to 0. It may be called again to start another run. Once it has been called, `mapPage` and `unmapPage` are not called again.
- With demand paging, `translate(address)` does the TLB step as before. When the page is not in memory, that is a page fault, and the page is loaded:
  1. It goes into the lowest-numbered free frame. When no frame is free, the policy chooses a victim, which is removed from the page table and from the TLB, and the page goes into the victim's frame.
  2. The translation then completes as for a page that was in memory: its entry is added to the TLB (after the victim's entry was removed, so that removal may leave room) and the physical address is returned. A translation never returns `-1` in this mode.
- Every translation of a page is a **use** of it, whether it hits the TLB, misses it, or loads the page.
- `resident()`: the pages in memory, sorted; before `useFrames`, the mapped pages.

The policies:

- **`fifo`** (first in, first out): the victim is the page that was loaded the earliest.
- **`lru`** (least recently used): the victim is the page whose last use is the earliest.
- **`clock`**: the frames form a circle, 0, 1, ..., `count - 1` and back to 0, with a **hand** that points at frame 0 when `useFrames` is called. Each frame has a **use bit**, set to 1 whenever its page is used, including when it is loaded. Filling a free frame does not move the hand. To choose a victim, look at the frame under the hand: if its use bit is 1, set it to 0 and move the hand to the next frame; repeat until the hand is on a frame whose bit is 0. That frame's page is the victim; the new page goes into that frame, with its use bit 1, and the hand moves one frame on.

**Belady's anomaly.** You would expect more frames to mean fewer faults. With FIFO it can be the other way round: on the references 1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5, three frames give 9 faults and four frames give 10. LRU never does this: the pages LRU keeps in `n` frames are always among those it keeps in `n + 1`, so more frames can only help. The clock is a cheap approximation of LRU: a use sets one bit, and only a fault has to look for a victim, while exact LRU must reorder its list on every use.

### Example 1

<!-- case: ex5 -->

Belady's anomaly. Each address is the first byte of the page with the same number. With 3 frames, FIFO faults 9 times; with 4 frames, 10 times. The physical addresses show where each page landed: with 4 frames, page 5 replaces page 1, the oldest, in frame 0.

### Example 2

<!-- case: ex6 -->

The same references under LRU and the clock, with 3 frames. When page 4 arrives, LRU evicts page 2, the least recently used, and then needs it again at once: 6 faults. The clock finds every use bit set, clears them all as it goes round, and evicts page 1 in frame 0, where its hand started; when page 5 arrives, page 2 has been used since (its bit is 1 again), so the hand clears it and takes page 3: 5 faults on this string.

## Level 4: Two-level tables and the working set

**Smaller page tables.** A one-level page table has an entry for every page of the address space, mapped or not. With 32-bit addresses, 4096-byte pages and 4-byte entries, that is 2^20 entries and 4 MiB per program. A **two-level** table cuts that list into pieces of one page each, the *inner tables*, and keeps only the pieces that hold at least one mapped page. A small **directory** says where each piece is. The page number is split again: its high bits index the directory, and its low bits index the inner table.

- `walk(address, entryBytes)`: the indexes of a translation through a two-level table whose entries take `entryBytes` bytes, as `[directory index, table index, offset]`. An inner table fills one page, so it holds `E = pageSize / entryBytes` entries: the table index is the page number modulo `E`, and the directory index is the page number divided by `E`, rounded down.
- `tableBytes(addressBits, entryBytes)`: the memory used by the page tables for the pages in the page table now (mapped, or in memory with demand paging), in an address space of `2^addressBits` bytes, as `[one level, two levels]`:
  - one level: one entry for every page of the address space, `2^addressBits / pageSize` entries of `entryBytes` bytes;
  - two levels: the directory, one entry of `entryBytes` bytes for each of the `2^addressBits / pageSize / E` inner tables there could be, plus `pageSize` bytes for each inner table that holds at least one page that is in the page table now. The directory takes exactly its entries' bytes, even when that is less or more than one page.

**The working set.** Programs use a few pages at a time, and the set changes slowly as they move from one task to the next. The **working set** of a program is the set of pages it used in its most recent references; it estimates how much memory the program needs right now.

- Every call to `translate` is one **reference** to the page of its address, including one that faults. `useFrames` starts a new run and forgets the references made before it.
- `workingSet(window)`: the distinct pages among the last `window` references, sorted; all the references when there are fewer.
- `thrashing(window)`: `true` when demand paging is on and the working set of the last `window` references has more pages than there are frames. Before `useFrames`, memory has no limit and the answer is `false`.

A program whose working set does not fit in its frames evicts pages it is about to use, and faults again and again: it *thrashes*, spending its time waiting for the disk. A system that sees it can stop some programs so that the others' working sets fit.

### Example 1

<!-- case: ex7 -->

32-bit addresses and 4096-byte pages: a one-level table with 4-byte entries takes 4194304 bytes (4 MiB). An inner table holds 4096 / 4 = 1024 entries, so the directory has 1024 entries, 4096 bytes. Pages 18 and 19 share inner table 0 and page 1048575 is in inner table 1023: two inner tables, 3 pages of tables in all. With 8-byte entries, an inner table holds 512 entries, and the directory 2048 entries, 16384 bytes.

### Example 2

<!-- case: ex8 -->

Three frames under LRU and a loop over four pages: every reference faults, the working set of the last 4 references has 4 pages, and the program is thrashing. When it moves on to a loop over pages 7 and 8, they stay in memory, and the last 4 references hold only 2 pages. Over the last 8 references, the working set still includes pages 2 and 3, from before the change.

## Constraints

- At most 2000 calls per test.
- `pageSize` is a power of two, `2 <= pageSize <= 65536`; `0 <= address < 2^48`; in `mapPage`, `0 <= page < 2^47` and `0 <= frame < 2^20`.
- `1 <= entries <= 64` and `1 <= count <= 64`.
- `entryBytes` is 1, 2, 4 or 8, at most `pageSize`; `addressBits <= 48`, and `2^addressBits` holds at least one whole inner table of pages: `2^addressBits >= pageSize * E`. When `tableBytes` is called, every page in the page table is below `2^addressBits / pageSize`.
- `1 <= window <= 10^5`.

## Follow-ups

- Belady's optimal policy evicts the page whose next use is furthest in the future. It cannot be built, since it needs the future; why is it still worth simulating?
- Suppose the use bit lives in the page table and is set only when a translation reads the page table, so that a TLB hit leaves it alone. What would that change in the clock, and what would the operating system have to do to the TLB when it clears a bit?
- A 48-bit address space with 4096-byte pages and 8-byte entries needs a directory of 1 GiB with two levels. How many levels make every table fit in one page?
- How would you pick the window of the working set, and what happens when it is too short or too long?
- Several programs share the memory. How would you divide the frames among them using their working sets?

## Hints

### Hint 1

Do the worked example by hand, then try address 70 with 32-byte pages. Division and remainder by the page size give the page and the offset; the frame times the page size, plus the offset, gives the physical address.

### Hint 2

A dictionary from page to frame is the page table. With `pageSize = 2^k`, `address >> k` is the page and `address & (pageSize - 1)` is the offset. Use 64-bit integers throughout.

### Hint 3

The TLB is a small map from page to frame that also remembers the order of use. An ordered map, or a list where a used entry moves to the end, gives the least recently used entry at the front. Whenever the page table changes a page, delete that page from the TLB.

### Hint 4

For demand paging, keep, for each frame, the page it holds. Free frames fill in order 0, 1, 2, ... and never become free again. When evicting, remove the victim from the page table and from the TLB before the new page takes its frame.

### Hint 5

FIFO needs the order in which pages were loaded; LRU needs the order in which they were last used, updated on every translation, TLB hit or not. The clock needs a use bit per frame and the position of the hand, which moves only while choosing a victim.

### Hint 6

For two-level tables, `E = pageSize / entryBytes`. The inner tables in use are the distinct values of `page / E` over the pages in the page table. The working set is a set built from the end of a list of every page translated since the run began.

### Hint 7

Keep one map for the page table, an ordered map for the TLB, a frame-to-page array, an ordered set of pages by load time, another by last use, a use-bit array, the hand, and a list of referenced pages. `translate`: record the reference; on a TLB hit, refresh the entry and mark the use; on a miss, read the page table; if the page is absent, count a fault and, in demand mode, load it into the next free frame or the victim's frame, dropping the victim from the table, the TLB and the orders; mark the use; add the TLB entry, evicting its front when full; return `frame * pageSize + offset`.
