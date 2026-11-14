# Review: the facts of the operating systems guides

The six guides of the path "Operating systems: from processes and scheduling to virtual memory and deadlock" ([guides](../specs/guides.md), [ADR 0025](../decisions/0025-concept-guides-and-learning-paths.md)) state facts about papers, POSIX, the Linux manual pages and kernel documentation, and Python's standard library. This page lists each one with where it was checked, so that the independent review starts from the sources.

"Quote" means the exact text was read at that source: on the web page, in the raw file fetched from it, or in the text extracted from a PDF with `pdftotext`. "Run" means an example of the guide, or a one-off program, printed it, on CPython 3.13.12. "Arithmetic" means the number was computed from the stated inputs. A fact that could not be checked was left out of the guides; the last sections list those, the names used, and where a guide comes close to a linked problem.

| Guide | Slug |
|-------|------|
| Processes, threads and system calls | `processes-and-system-calls` |
| CPU scheduling | `cpu-scheduling` |
| Virtual memory, paging and page replacement | `virtual-memory` |
| Memory allocators: free lists, fragmentation and buddies | `memory-allocation` |
| Locks, condition variables and semaphores | `locks-and-condition-variables` |
| Deadlock | `deadlock` |

## Processes and system calls

POSIX.1-2024 (The Open Group Base Specifications Issue 8) at pubs.opengroup.org; the Linux manual pages at man7.org; Python 3.13's documentation; and the free textbook *Operating Systems: Three Easy Pieces*, version 1.10, as a secondary source. Used in `processes-and-system-calls`, and where noted in other guides.

| # | Claim | Source |
|---|-------|--------|
| PS1 | `fork` creates a new process that is an exact copy of the caller except as listed: a unique process id, the caller as parent, its own copy of the file descriptors, each referring to the same open file description; it returns 0 to the child and the child's id to the parent, and both continue from `fork` | Quote: [POSIX, `fork`](https://pubs.opengroup.org/onlinepubs/9799919799/functions/fork.html) |
| PS2 | A multi-threaded process that forks gets a child with a replica of the calling thread and its entire address space, possibly including the states of mutexes; the child may only execute async-signal-safe operations until it calls an `exec` function | Quote: POSIX, `fork` |
| PS3 | The `exec` functions replace the current process image; there is no return from a successful `exec`; open file descriptors stay open unless `FD_CLOEXEC` is set; the process id is inherited | Quote: [POSIX, `exec`](https://pubs.opengroup.org/onlinepubs/9799919799/functions/exec.html) |
| PS4 | `wait` and `waitpid` obtain status information about a child; `wait` blocks until it is available | Quote: [POSIX, `waitpid`](https://pubs.opengroup.org/onlinepubs/9799919799/functions/waitpid.html) |
| PS5 | An exiting process becomes a zombie whose status is available until its parent obtains it; its children and zombies are inherited by an implementation-defined system process | Quote: [POSIX, `_exit`](https://pubs.opengroup.org/onlinepubs/9799919799/functions/_exit.html) |
| PS6 | Parent and child run in separate memory spaces with the same content at the fork, and writes by one do not affect the other; the child is created with a single thread; its descriptors refer to the same open file descriptions, sharing status flags and the file offset; `fork` uses copy-on-write pages, so its only penalty is duplicating the page tables and creating a task structure | Quote: [`fork(2)`](https://man7.org/linux/man-pages/man2/fork.2.html) |
| PS7 | A child that ends and is not waited for becomes a zombie, of which the kernel keeps the id, the termination status and resource usage; zombie children of a terminated parent are adopted by `init` or a subreaper, and `init` waits for them | Quote: [`wait(2)`](https://man7.org/linux/man-pages/man2/wait.2.html) |
| PS8 | A system call is an entry point into the kernel, the fundamental interface between an application and the kernel; a C library wrapper copies the arguments and the call's number into registers, traps to kernel mode, and sets `errno` on error | Quote: [`intro(2)`](https://man7.org/linux/man-pages/man2/intro.2.html), [`syscalls(2)`](https://man7.org/linux/man-pages/man2/syscalls.2.html) |
| PS9 | The threads of a process share its global memory, data and heap, but each has its own stack | Quote: [`pthreads(7)`](https://man7.org/linux/man-pages/man7/pthreads.7.html) |
| PS10 | `clone` creates a child "in a manner similar to fork" with control over sharing the address space, the descriptor table and the signal handlers; `CLONE_VM` shares the memory space, `CLONE_THREAD` puts the child in the caller's thread group; one use is to implement threads | Quote: [`clone(2)`](https://man7.org/linux/man-pages/man2/clone.2.html) |
| PS11 | The vDSO is a small shared library the kernel maps into every user-space program; some calls are so frequent that their cost, including the overhead of leaving user space and entering the kernel, dominates; the kernel places the information in memory the process can read, so `gettimeofday` becomes a function call and a few memory reads | Quote: [`vdso(7)`](https://man7.org/linux/man-pages/man7/vdso.7.html) |
| PS12 | A file descriptor is a small non-negative integer indexing the process's table of open descriptors; a new one is the lowest-numbered one not open | Quote: [`open(2)`](https://man7.org/linux/man-pages/man2/open.2.html) |
| PS13 | `os.fork` returns 0 in the child and its id in the parent; since 3.12 it raises a `DeprecationWarning` when it detects several threads; `os.waitstatus_to_exitcode` returns the exit status, or `-signum`; `os._exit` exits without cleanup handlers or flushing stdio buffers and is normally used in a child after `fork` | Quote: [Python, `os`](https://docs.python.org/3/library/os.html) |
| PS14 | Standard output is line-buffered when interactive and block-buffered otherwise | Quote: [Python, `sys.stdout`](https://docs.python.org/3/library/sys.html#sys.stdout) |
| PS15 | The global interpreter lock lets only one thread execute Python bytecode at a time; as of 3.13, experimental free-threaded builds can disable it | Quote: [Python, `threading`](https://docs.python.org/3/library/threading.html) |
| PS16 | User mode is restricted (an I/O request raises an exception and the OS likely kills the process); kernel mode is not; trap and return-from-trap instructions; a timer interrupt every so many milliseconds lets the OS regain control; a context switch saves registers of the current process and restores those of the next; the states running, ready and blocked | Quote: the textbook, chapters *The Abstraction: The Process* and *Mechanism: Limited Direct Execution* |
| PS17 | A system may invalidate all TLB entries on a context switch; some TLBs tag entries with an address space identifier instead | Quote: the textbook, *Paging: Faster Translations (TLBs)* (also in `virtual-memory`) |

## CPU scheduling

Corbató, Merwin-Daggett and Daley's 1962 paper, read in the transcription "scanned and transcribed by F. J. Corbató from the original SJCC paper of May 3, 1962", hosted on a course site ([PDF](https://fisop.github.io/apunte/_downloads/6d5506d6d15a071fdc73ad3ca31c9793/doc.pdf)); the guide cites the DOI. Used in `cpu-scheduling`.

| # | Claim | Source |
|---|-------|--------|
| C1 | A multi-level scheduling algorithm: a program enters a level ℓ0 computed from its size and the words that can be moved in one quantum; the supervisor runs the head of the lowest occupied level for up to 2^ℓ quanta, and an unfinished program goes to the end of the ℓ + 1 queue; when a lower level becomes occupied, the current program is put back at the head of its queue; since a program always runs at least its swap time, efficiency never falls below one half; simple round robin near saturation collapses abruptly because of swapping; long runs must in effect prove they are long | Quote: Corbató and others, *A Multi-Level Scheduling Algorithm* |
| C2 | Linux policies: `SCHED_OTHER` (standard time-sharing, dynamic priority based on the nice value and increased for each quantum a thread is ready but denied), `SCHED_BATCH`, `SCHED_IDLE`; `SCHED_FIFO` and `SCHED_RR` with static priorities 1 to 99, above normal threads; `SCHED_FIFO` runs until it blocks, is preempted by a higher priority or yields, `SCHED_RR` adds a maximum time quantum; conceptually one list per static priority; POSIX requires only 32 real-time levels; nice from −20 to +19, each unit a factor of 1.25 in the current implementation; real-time threads can block others forever, and `RLIMIT_RTTIME` (since 2.6.25) caps their CPU time; `SCHED_DEADLINE` uses global EDF with a constant bandwidth server, an admission test, and preempts every other policy | Quote: [`sched(7)`](https://man7.org/linux/man-pages/man7/sched.7.html) |
| C3 | With `PTHREAD_PRIO_INHERIT`, a thread that blocks higher-priority threads by owning such a mutex runs at the priority of the highest one waiting | Quote: [POSIX, `pthread_mutexattr_getprotocol`](https://pubs.opengroup.org/onlinepubs/9799919799/functions/pthread_mutexattr_getprotocol.html) |
| C4 | The convoy effect; SJF is optimal when all jobs arrive at the same time; STCF is provably optimal; response time as a metric; a time slice long enough to amortize the cost of switching | Quote: the textbook, *Scheduling: Introduction* |
| C5 | The feedback queue's rules, with the allotment counted regardless of how many times the job gave up the CPU; the priority boost after each period S against starvation | Quote: the textbook, *Scheduling: The Multi-Level Feedback Queue* |
| C6 | A process builds up state in a CPU's caches and TLB; one shared queue needs locking and scales poorly; per-CPU queues bring load imbalance, which migration and work stealing address | Quote: the textbook, *Multiprocessor Scheduling (Advanced)* |

## Virtual memory and page replacement

The Linux kernel documentation at docs.kernel.org (7.4.0-rc2 at the time of reading); the Linux manual pages; Mattson, Gecsei, Slutz and Traiger's paper, read from a scan of the IBM Systems Journal issue (`ibmsj0902B.pdf` on bitsavers.org); Denning's two 1968 papers, read from PDFs on a course site at cs.uwaterloo.ca; the Belady, Nelson and Shedler abstract from Crossref's metadata. Used in `virtual-memory`.

| # | Claim | Source |
|---|-------|--------|
| V1 | Page tables map virtual addresses to physical ones; Linux's hierarchy is currently five levels, folded where an architecture uses fewer; large unmapped areas are marked at a higher level; the pfn is the physical address divided by `PAGE_SIZE`, so pfn 1 is at 0x1000 with 4 KiB pages; an entry holds a pfn and protection bits | Quote: [*Page Tables*](https://docs.kernel.org/mm/page_tables.html) |
| V2 | The MMU uses TLBs and page walk caches and walks the tables on a miss; page faults when access is not permitted or the data is not present; lazy allocation and copy-on-write are expected causes, swapping an undesirable one under pressure; the dirty bit is set when a page is written | Quote: *Page Tables*, *MMU, TLB, and Page Faults* |
| V3 | Four-level paging limited one 64-bit processor family to 256 TiB of virtual address space; five levels raise it to 128 PiB | Quote: [*5-level paging*](https://docs.kernel.org/arch/x86/x86_64/5level-paging.html) |
| V4 | After software page table changes, the kernel flushes the TLB, since stale translations may exist | Quote: [*Cache and TLB Flushing Under Linux*](https://docs.kernel.org/core-api/cachetlb.html) |
| V5 | The examples presume a basic page of 4K and a huge page of 2M, which vary by architecture; with huge pages a TLB miss runs faster and one entry maps much more memory | Quote: [*Transparent Hugepage Support*](https://docs.kernel.org/admin-guide/mm/transhuge.html) |
| V6 | A page is the unit of allocation and mapping; a program should not hard-code the page size, since some architectures support several | Quote: [`getpagesize(2)`](https://man7.org/linux/man-pages/man2/getpagesize.2.html); `sysconf(_SC_PAGE_SIZE)` in [`mmap(2)`](https://man7.org/linux/man-pages/man2/mmap.2.html) |
| V7 | `MAP_PRIVATE` is a private copy-on-write mapping whose updates do not reach the file; `MAP_ANONYMOUS` is backed by no file and zero-filled | Quote: `mmap(2)` |
| V8 | Minor faults are serviced without I/O, by reclaiming a frame from the pages awaiting reallocation; major faults required I/O | Quote: [`getrusage(2)`](https://man7.org/linux/man-pages/man2/getrusage.2.html) |
| V9 | The working set W(t, τ) is the information referenced during the process time interval (t − τ, t); FIFO retires the page least recently paged in; LRU uses a use bit set on each reference, with entries searched at intervals; Belady's study concluded that a good algorithm needs much of the simplicity of random or FIFO selection and some, though not much, history | Quote: [Denning, *The working set model for program behavior*](https://doi.org/10.1145/363095.363141), §2 and §3 |
| V10 | Thrashing is excessive overhead and severe performance degradation or collapse caused by too much paging; there must be space for every active process's working set; global FIFO or LRU make this hard to control; the cause is traced to the very large speed difference between main and auxiliary storage | Quote: [Denning, *Thrashing: its causes and prevention*](https://doi.org/10.1145/1476589.1476705) |
| V11 | Stack algorithms (LFU, LRU, OPT, random) have the inclusion property and monotonic success functions, and are evaluated for every capacity in one pass of a trace; FIFO is not one, shown by the trace `abcdabeabcde` after Belady, Nelson and Shedler; Belady describes an optimum algorithm called MIN; OPT pushes the page whose next reference is farthest, is proved optimal, and is evaluated in two passes | Quote: [Mattson and others, *Evaluation techniques for storage hierarchies*](https://doi.org/10.1147/sj.92.0078), *first-in/first-out* and *An optimum replacement algorithm* |
| V12 | Running time generally increases as the store decreases, but experiments revealed cases where a smaller store ran faster; the paper gives a formal treatment for FIFO | Quote: [Belady, Nelson and Shedler](https://doi.org/10.1145/363011.363155), abstract (Crossref) |
| V13 | The hardware sets the use bit and the OS clears it; the clock algorithm, credited to Corbató; perfect LRU needs work on every memory access; the dirty bit, and evicting clean pages first | Quote: the textbook, *Beyond Physical Memory: Policies* |
| V14 | Temporal and spatial locality; a fully associative TLB searched in parallel; after a miss or a fault is handled, the instruction is retried | Quote: the textbook, *Paging: Faster Translations (TLBs)* and *Beyond Physical Memory: Mechanisms* |

## Memory allocators

Wilson, Johnstone, Neely and Boles's survey, read from a PDF copy on a course site at cs.northwestern.edu; Bonwick's paper from the USENIX legacy site, and the conference from its proceedings index; the Linux manual pages. Used in `memory-allocation`.

| # | Claim | Source |
|---|-------|--------|
| A1 | External fragmentation: free blocks that cannot hold the sizes requested; internal fragmentation: a block larger than needed; both are fought by splitting and coalescing | Quote: [Wilson and others](https://doi.org/10.1007/3-540-60368-9_19), §2.1 |
| A2 | A conventional allocator cannot compact memory by moving blocks, as copying garbage collectors do | Quote: Wilson and others, introduction |
| A3 | Address-ordered first fit tends to pack one end of memory with live data | Quote: Wilson and others, a footnote to the discussion of sequential fits |
| A4 | Next fit keeps a roving pointer (Knuth) where the last search ended, to decrease search times; in several experiments with real and synthetic traces it caused more fragmentation | Quote: Wilson and others, §3.4 |
| A5 | Best fit and policies like it generally use indexed or segregated fits to be fast | Quote: Wilson and others, sequential fits |
| A6 | Boundary tags, due to Knuth: a header and a footer with the size and the used flag; freeing reads the footer before and the header after; the footer can be avoided, an optimization described by Standish | Quote: Wilson and others, §3.2 |
| A7 | A splitting threshold: blocks are not split when the rest would be too small | Quote: Wilson and others, sequential fits |
| A8 | Segregated free lists; simple segregated storage requests one or two pages at a time, splits them into same-sized blocks, needs no headers, and in the worst case uses memory proportional to the live data times the number of size classes | Quote: Wilson and others, §3.6 |
| A9 | An allocator described in the survey divides each power of two into four ranges | Quote: Wilson and others, a footnote near §3.6 and §3.7 |
| A10 | Binary buddies have power-of-two sizes and find a buddy by address computation, one offset bit per level; expected internal fragmentation of very roughly 28%; buddy systems generally fragment more than segregated fits and boundary tags, mostly in synthetic studies; Knowlton published the first paper on the binary buddy system and suggested deferred coalescing for objects of the same size used again and again | Quote: Wilson and others, §3.7 and the history in §4 |
| A11 | Requests larger than `MMAP_THRESHOLD`, 128 kB by default and adjustable with `mallopt`, are private anonymous `mmap` mappings; freeing a pointer twice, or one not from `malloc`, is undefined behavior | Quote: [`malloc(3)`](https://man7.org/linux/man-pages/man3/malloc.3.html) |
| A12 | `mmap`ed blocks can be released independently; the heap can be trimmed only when memory is freed at its top end | Quote: [`mallopt(3)`](https://man7.org/linux/man-pages/man3/mallopt.3.html) |
| A13 | `brk` and `sbrk` move the program break, the end of the data segment; raising it allocates memory | Quote: [`brk(2)`](https://man7.org/linux/man-pages/man2/brk.2.html) |
| A14 | `/proc/buddyinfo` helps diagnose fragmentation; it counts free chunks of each order per zone, a chunk being 2^order pages; the kernel's binary buddy allocator splits and combines chunks | Quote: [`proc_buddyinfo(5)`](https://man7.org/linux/man-pages/man5/proc_buddyinfo.5.html) |
| A15 | Object caching keeps an object's constructed state between uses, since construction can cost much more than allocation; a slab is one or more pages carved into equal-size chunks with a reference count; presented at the USENIX Summer 1994 Technical Conference | Quote: [Bonwick, *The Slab Allocator*](https://www.usenix.org/legacy/publications/library/proceedings/bos94/full_papers/bonwick.a), §2 and the description of the slab; the [proceedings index](https://www.usenix.org/legacy/publications/library/proceedings/bos94/) |

## Locks, condition variables and semaphores

Dijkstra's manuscripts from the E. W. Dijkstra Archive at cs.utexas.edu, with publication data from its BibTeX index; Lampson and Redell's paper from its author's site ([web page](https://bwlampson.site/23-ProcessesInMesa/WebPage.html)); Hoare's and Courtois, Heymans and Parnas's abstracts from Crossref's metadata. Used in `locks-and-condition-variables`, and in `deadlock` where noted.

| # | Claim | Source |
|---|-------|--------|
| L1 | Two processes executing `S1 := S1 + 1` can lose an increase; V increases a semaphore by 1 indivisibly; P decreases it by 1 as soon as the result is non-negative, indivisibly, and which waiting P completes is unspecified; binary and general semaphores, with Scholten credited for the general ones; Dekker gave the first correct solution for two processes; the notes have sections on the deadly embrace and the banker's algorithm; published in *Programming Languages* (Genuys, ed.), Academic Press, 1968 | Quote: [EWD 123](https://www.cs.utexas.edu/~EWD/transcriptions/EWD01xx/EWD123.html); [BibTeX index](https://www.cs.utexas.edu/~EWD/indexBibTeX.html) |
| L2 | `pthread_mutex_lock` blocks while another thread holds the mutex; relocking: normal deadlocks, error-checking returns an error (`EDEADLK`), recursive counts, default is undefined or one of the others | Quote: [POSIX, `pthread_mutex_lock`](https://pubs.opengroup.org/onlinepubs/9799919799/functions/pthread_mutex_lock.html) (also in `deadlock`) |
| L3 | `pthread_cond_wait` atomically releases the mutex and blocks; a Boolean predicate goes with each wait; spurious wake-ups may occur and the predicate should be re-evaluated on return | Quote: [POSIX, `pthread_cond_wait`](https://pubs.opengroup.org/onlinepubs/9799919799/functions/pthread_cond_wait.html) |
| L4 | Signal unblocks at least one waiter, broadcast all; the scheduling policy sets the order; an unblocked thread owns the mutex on return; on a multiprocessor a signal may unblock more than one | Quote: [POSIX, `pthread_cond_signal`](https://pubs.opengroup.org/onlinepubs/9799919799/functions/pthread_cond_signal.html) |
| L5 | `sem_wait` locks if the value is positive, else blocks; `sem_post` increments, or lets one waiter return; under the process scheduling option, `SCHED_FIFO` and `SCHED_RR` wake the highest-priority waiter | Quote: POSIX, [`sem_wait`](https://pubs.opengroup.org/onlinepubs/9799919799/functions/sem_wait.html), [`sem_post`](https://pubs.opengroup.org/onlinepubs/9799919799/functions/sem_post.html) |
| L6 | `Lock`: acquire blocks while locked, which waiter proceeds is not defined, `acquire(timeout=...)` returns `False` on timeout; `RLock` may be acquired several times by the same thread | Quote: Python, `threading` (also in `deadlock`) |
| L7 | `Condition`: the typical style calls `wait` repeatedly until the desired state; `notify` wakes one, `notify_all` all; `notify` does not release the lock and is a no-op without waiters; `wait_for` loops on a predicate | Quote: Python, `threading` |
| L8 | `Semaphore`: a counter that never goes below zero; `acquire` blocks at zero; one thread is woken per `release`, in an order not to be relied on; `blocking=False` returns `False` at once | Quote: Python, `threading` |
| L9 | `Barrier`: a fixed number of threads block until all have called `wait`, then are released together; reusable | Quote: Python, `threading` (in `deadlock`) |
| L10 | A monitor's data is reachable only through its procedures, one process at a time; Hoare's signal runs the waiter at once; Mesa's notify is a hint, the waiter resumes later, reacquires the lock, and another process may enter first, so waiting is `while not <OK to proceed> do wait`; covering conditions with a cheap predicate, each waiter checking its exact condition | Quote: [Lampson and Redell](https://doi.org/10.1145/358818.358824), the description of monitors and §4 |
| L11 | Hoare develops Brinch Hansen's monitor as a way to structure an operating system; examples include a bounded buffer and readers and writers | Quote: [Hoare, *Monitors*](https://doi.org/10.1145/355620.361161), abstract (Crossref) |
| L12 | Readers may share the section, writers need it alone; one solution minimizes the delay of readers, the other lets writing happen as early as possible | Quote: [Courtois, Heymans and Parnas](https://doi.org/10.1145/362759.362813), abstract (Crossref) |
| L13 | Futexes are a building block for mutexes, condition variables, read-write locks, barriers and semaphores, used through system libraries; the uncontended case runs entirely in user space and the kernel arbitrates the contended one; an aligned four-byte integer changed with atomic instructions | Quote: [`futex(7)`](https://man7.org/linux/man-pages/man7/futex.7.html) (also in `processes-and-system-calls`) |
| L14 | Test-and-set writes a new value and returns the old one atomically; a two-phase lock spins first, then sleeps | Quote: the textbook, *Locks* |

## Deadlock

Coffman, Elphick and Shoshani's survey, read from a PDF copy of the article (a mirror of a Stanford reading list on carlstrom.com); Dijkstra's EWD 623 and EWD 310 from the archive. Used in `deadlock`.

| # | Claim | Source |
|---|-------|--------|
| D1 | The disk-channel and shared-file example; Dijkstra called deadlocks deadly embraces; resources include devices, processors, storage, programs and data | Quote: [Coffman and others, *System Deadlocks*](https://doi.org/10.1145/356586.356588), §1 |
| D2 | The four conditions: mutual exclusion, "wait for", no preemption, circular wait | Quote: Coffman and others, §2 |
| D3 | The state graph: an arc from Ri to Rj when a task holds Ri and requests Rj; with one resource of each type, a circuit has been shown to be necessary and sufficient, given the first three conditions; with several units, it is only necessary, and detection uses matrices of holdings and excess requests | Quote: Coffman and others, §2 and §4 |
| D4 | Prevention keeps one condition false; mutual exclusion cannot be denied for all resources (a shared file only while nobody updates it); Havender's three approaches, with their costs: resources unused for long periods, convenient only for resources whose state is easily saved, such as a processor; a linear order leaves the state graph without circuits | Quote: Coffman and others, §3 |
| D5 | Detection maintains the state graph and looks for a circuit; recovery aborts the deadlocked tasks, or some in sequence, or preempts the resources of least cost | Quote: Coffman and others, §4 |
| D6 | Avoidance usually needs advance information; the safe state; only safe requests may be scheduled by the secondary criteria; Habermann's model knows only each task's maximum, needs no back-up in its search, takes time proportional to the square of the number of tasks, and has false threats of deadlock | Quote: Coffman and others, §5 |
| D7 | Prevention is better than cure where possible; deadlock is exceptional and involves a limited set of resources; detection or avoidance when prevention's constraints are unacceptable | Quote: Coffman and others, §6 |
| D8 | The banker has `cap` units; a need is the most units a process may hold at once, and loans never exceed it; a pattern is safe if a granting strategy can guarantee every request; one failing ordering attempt proves it unsafe without back-tracking; the search for a request from `c` can stop once `c` is placed, a discovery credited to L. Zwanenburg in the early sixties | Quote: [EWD 623](https://www.cs.utexas.edu/~EWD/transcriptions/EWD06xx/EWD623.html) |
| D9 | Five philosophers, a dish needing two forks; taking the left fork then the right is rejected for the deadly embrace when all grab their left fork; a combined P on both forks; a philosopher eats only when neither neighbor eats | Quote: [EWD 310](https://www.cs.utexas.edu/~EWD/transcriptions/EWD03xx/EWD310.html) |
| D10 | Trying the second lock and releasing the first on failure; livelock; a random delay before retrying | Quote: the textbook, *Common Concurrency Problems* |

## The examples and the arithmetic

| # | Claim | Source |
|---|-------|--------|
| E1 | The child prints 11 and exits with 7; the parent's counter stays 10; both threads' names are in the shared list | Run: `fork_and_threads.py` |
| E2 | Arrival order waits 10.25 on average, turnaround 16.25; shortest first 7 and 13; round robin with a quantum of 4 responds in 6 on average with a turnaround of 19.25; no order of the 24 beats D A C B | Run: `three_policies.py` |
| E3 | Swapping an adjacent longer-then-shorter pair lowers the total waiting by the difference of their bursts; waiting and turnaround differ by the sum of the bursts | Arithmetic |
| E4 | Row by row: 512 page changes, 2 pages in the first 1000 reads; column by column: 262144 and 512 | Run: `locality.py` |
| E5 | FIFO faults 9 with 3 frames and 10 with 4; LRU 10 and 8; optimal 7 and 6 | Run: `replacement.py` |
| E6 | 0x4E20 = 20000 = 4 × 4096 + 3616; 9 × 4096 + 3616 = 40480 = 0x9E20 | Arithmetic |
| E7 | 4096 / 8 = 512 entries, 9 bits per level; 4 × 9 + 12 = 48 bits, 2^48 bytes = 256 TiB; 5 × 9 + 12 = 57 bits, 128 PiB | Arithmetic |
| E8 | 11594 bytes asked; 86, 5526 and 358 wasted; 512, 10 and 37 block sizes | Run: `size_classes.py` |
| E9 | Slots 3 and 1 are reused last-freed first; a second free of slot 0 is refused | Run: `object_pool.py` |
| E10 | Without a lock x ends at 1; with it, 2 | Run: `race.py` |
| E11 | The latch returns once three workers reported | Run: `latch.py` |
| E12 | Never more than 2 workers inside; a second acquire without waiting fails | Run: `permits.py` |
| E13 | Opposite orders: both tries time out; one order: both threads finish | Run: `two_locks.py` |
| E14 | With 3 units free, R's request for 1 is unsafe and P's is safe, in the order Q P R | Run: `banker.py`; arithmetic in the guide |

## Citations and names

The guides name no company and no product. Where they name software, it is POSIX, Linux, whose manual pages and kernel documentation are the sources for its behavior, and Python, the language of the examples. Papers are cited by their authors. The textbook *Operating Systems: Three Easy Pieces* is a secondary source, named only by its title; its address carries its authors' directory.

| Left out | Where it appears in a source |
|----------|------------------------------|
| The machine and system names of the 1962 paper | Corbató and others |
| The operating system of Havender's example, and its macros | Coffman and others |
| The operating system and workstation of the slab paper | Bonwick |
| The systems named in the thrashing paper | Denning |
| The processor family of five-level paging | The kernel's *5-level paging* page; the guide says "one 64-bit processor family" |
| The name of the allocator with four classes per doubling, and of the language system of an early buddy allocator | Wilson and others |
| The name of the C library | The Linux manual pages; the guides say "the C library" |

## Not verified, so left out or reworded

- The DOI pages at the ACM Digital Library refused the requests (HTTP 403). The papers were read from other copies, named above; for Hoare, for Courtois, Heymans and Parnas, and for Belady, Nelson and Shedler, only the abstract was read, from Crossref, and the guides state only what the abstracts say. Knowlton's paper was not read; the guide states only what the survey says of it.
- Belady's 1966 paper could not be read: the scan of its journal issue lacks it. The guide says only what Mattson and others and Denning say of it; how the paper evaluated the algorithms was not checked and is not stated.
- The 1962 paper's formula for the first level is an image missing from the transcription: the guide says only that the level is computed from the program's size and what can be moved in one quantum. The guide calls the system, in the paper's words, an experimental time-sharing system; whether it was among the first was not checked.
- The transcription of EWD 123 carries no date; the guide cites its publication in 1968 from the archive's index. Its section on the banker's algorithm is not in the transcription read; the guide cites EWD 623 for the algorithm.
- The name of Linux's current default scheduler is not stated: `sched(7)` names the one introduced in 2.6.23, and no source read says what replaced it.
- Priority inversion is explained from the definition of priorities; only the inheritance protocol is cited, from POSIX.
- The survey's percentages for single allocators in one study were left out; only its "very roughly 28%" for binary buddies is used.
- The full title of Hoare's paper is not in Crossref's metadata, which gives *Monitors*; the guide uses that.
- No primary source on work stealing was read; the guide mentions moving work between queues in general, with the textbook as its source.
- Python's documentation does not say that `x += 1` can be interrupted between threads, so the race example simulates its threads with generators.
- Whether shells rely on the lowest free descriptor was not checked; the guide states only the consequence of the `open(2)` rule.

## Practice links and back-links

The path's problems are on main. Their `meta.yaml` gained these `guides:` entries, after `related:` where the problem had none, or at the end of its existing list:

| Problem | `guides:` |
|---------|-----------|
| 0092 `single-threaded-cpu` | `[heaps, cpu-scheduling]` |
| 0359 `cpu-scheduler-sim` | `[cpu-scheduling]` |
| 0002 `lru-cache` | `[designing-with-hash-maps, virtual-memory]` |
| 0360 `virtual-memory-sim` | `[virtual-memory]` |
| 0383 `memory-allocator` | `[memory-allocation]` |
| 0205 `concurrency-limiter` | `[locks-and-condition-variables]` |
| 0201 `bounded-blocking-queue` | `[locks-and-condition-variables]` |
| 0204 `read-write-lock` | `[locks-and-condition-variables]` |
| 0200 `thread-safe-lru-cache` | `[locks-and-condition-variables]` |
| 0202 `bank-transfers` | `[deadlock]` |

## Where a guide comes close to a linked problem

Each linked problem's statement, hints and solutions were read before writing. Each guide teaches its idea with examples of its own, but some ideas are the problem's subject. These are the places the review should weigh against the rule that a guide never gives away a linked problem's solution:

| Guide | Close to | What the guide shows |
|-------|----------|----------------------|
| `cpu-scheduling` | `cpu-scheduler-sim` levels 1 and 2 | First come, first served, shortest first and round robin for jobs that all arrive at 0, so none of the problem's arrival handling, tie rules (arrivals before the preempted process), segment merging, switch counting or API; its jobs and numbers differ from the problem's examples |
| `cpu-scheduling` | `cpu-scheduler-sim` level 3, follow-ups 3 and 5 | The feedback queue and the boost in prose, as the statement describes them; the allotment counted over all turns is stated without the reason follow-up 3 asks for; Corbató's doubling quanta and his swap-time argument touch follow-up 5 in general; his rule of returning an interrupted program to the head of its queue differs from the problem's, and the guide says to follow the problem |
| `cpu-scheduling` | `cpu-scheduler-sim` level 4 | One paragraph on per-core queues, imbalance and moving work, the background the level's statement gives; no placement or stealing rule |
| `cpu-scheduling` | `single-threaded-cpu` hint 2 | The complexity table gives O(log n) with a heap for choosing the shortest job, a general cost; the practice line states only the question |
| `virtual-memory` | `virtual-memory-sim` levels 1 and 4, follow-up 3 | A translation by hand with 4096-byte pages, as the statement does with 32-byte pages; why tables have levels, and the four-level arithmetic for 48-bit addresses, which answers follow-up 3 in general; no `walk` or `tableBytes` formula |
| `virtual-memory` | `virtual-memory-sim` level 3, follow-up 1 | Fault counts of FIFO (a queue), LRU (stack distances) and the optimal policy on the anomaly string the statement uses, with no frames, addresses, TLB or clock hand; the clock in prose; the optimal policy as a yardstick answers follow-up 1 in general |
| `virtual-memory` | `lru-cache` | LRU as a policy and its cost per access; no hash map and linked list |
| `memory-allocation` | `memory-allocator` levels 1 to 4 | Rounding rules other than the problem's (multiples of 16, powers of two, four classes per doubling) without headers; a pool of equal slots, not variable blocks; placement policies, boundary tags and buddies in prose, as the statement describes them; no split rule, rover rule, report formula or code |
| `locks-and-condition-variables` | `bounded-blocking-queue` hints 1 to 3 | The `while` loop around a wait, from POSIX and the Mesa paper; a countdown latch, not a bounded buffer; no "not full" and "not empty" conditions, no semaphores counting slots and items |
| `locks-and-condition-variables` | `concurrency-limiter` hints 1 and 2 | Using Python's semaphore, and that its wake order is not promised; no hand-off or waiter queue |
| `locks-and-condition-variables` | `read-write-lock` | Courtois, Heymans and Parnas's two preferences; no counters or wake-up rules |
| `locks-and-condition-variables` | `thread-safe-lru-cache` hint 3, follow-up 1 | The general rule that state tied by one invariant needs one lock; no cache structure; nothing on why a read-write lock would not help |
| `deadlock` | `bank-transfers` hints 2 and 3, follow-up 3 | One global order over two generic locks, R1 and R2; no accounts, balances or consistent total; detection and timeouts in general touch follow-up 3 |

## Independent accuracy review

Pending: the owner runs it.
