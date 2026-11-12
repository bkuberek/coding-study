# Review: the facts of the trees and heaps guides

The six guides of the path "Trees and heaps: from your first tree to a bank that schedules on a heap" ([guides](../specs/guides.md), [ADR 0025](../decisions/0025-concept-guides-and-learning-paths.md)) state facts about languages, libraries, definitions and one paper. This page lists each one with where it was checked, records which problems the path links and why others were left out, and holds the spoiler check of every linked problem, so that an independent review starts from the sources.

"Quote" means the exact text was read on that page. "Run" means an example of the guide printed it, on CPython 3.13.12. "Reasoning" means the guide proves it in plain words, and the proof was checked. A fact that could not be checked was left out of the guides.

| Guide | Slug | Level | Practice |
|-------|------|-------|----------|
| Trees and binary trees | `trees` | intro | none |
| Tree traversals | `tree-traversals` | core | 3 problems |
| Recursion on trees: values up, state down | `recursion-on-trees` | core | 11 problems |
| Binary search trees | `binary-search-trees` | core | 3 problems |
| Heaps and priority queues | `heaps` | core | 3 problems |
| Heap patterns: top k and two heaps | `heap-patterns` | advanced | 8 problems |

## Python

| # | Claim | Source |
|---|-------|--------|
| P1 | `heapq` keeps a min-heap in a list with `heap[k] <= heap[2*k+1]` and `heap[k] <= heap[2*k+2]`, counting from zero; `heap[0]` is the smallest; it compares only with `<`, like `list.sort()` | Quote: [heapq](https://docs.python.org/3/library/heapq.html); run: `min_heap.py` |
| P2 | `heapify` transforms a list in place, in linear time | Quote: heapq; run: `build_cost.py` |
| P3 | `heappushpop` runs more efficiently than a push then a pop and returns the smaller of the two; `heapreplace` pops then pushes, is more efficient than the two calls, "can be more appropriate when using a fixed-size heap", and may return a value larger than the one pushed | Quote: heapq, and the `heapreplace` docstring in [`Lib/heapq.py`](https://github.com/python/cpython/blob/main/Lib/heapq.py); run: `podium.py` |
| P4 | Max-heap functions named with `_max` (`heapify_max`, `heappush_max`, `heappop_max`, `heappushpop_max`, `heapreplace_max`) were added in 3.14 | Quote: heapq |
| P5 | `(priority, task)` tuples break when priorities tie and tasks cannot be compared; the documented fix is a 3-element entry with an entry count as tie-breaker | Quote: heapq; run: `triage.py` (`TypeError` on the tie of Kofi and Tomas; FIFO among equals with the counter) |
| P6 | A heapsort made of pushes and pops is, unlike `sorted()`, not stable | Quote: heapq |
| P7 | The top-k functions perform best for small n, `sorted()` for large n, `min()` and `max()` for n = 1 | Quote: heapq |
| P8 | Heaps suit schedulers: the heap holds pending events, the smallest scheduled time wins, and new events go in as they are created | Quote: heapq, section "Theory" |
| P9 | CPython's sift moves the smaller child up until the hole reaches a leaf, then sifts the item up, because the item moved in during a pop tends to be large; Knuth vol. 3 is the reference given | Quote: `Lib/heapq.py` comments above `_siftup`; run: `min_heap.py` pops in the same order as `heapq` |
| P10 | In random order the i-th value is among the k largest of the first i with probability k/i, giving about k(H(n) − H(k)) replacements; measured comparisons for k = 100: 5.7% more than `min()` at 100,000 items, 0.8% at 1,000,000; the worst case is reversed input | Quote: `Lib/heapq.py`, "Algorithm notes for nlargest() and nsmallest()"; run: `podium.py` (114 operations for n = 1,000,000 and k = 10, against about 124.6 expected; 100,000 of 100,000 for ascending input) |
| P11 | `deque` appends and pops at either end in approximately O(1); `list.pop(0)` and `insert(0, v)` cost O(n) | Quote: [collections](https://docs.python.org/3/library/collections.html#collections.deque) |
| P12 | The recursion limit prevents infinite recursion from overflowing the C stack; the highest limit is platform-dependent and a too-high limit can crash | Quote: [sys](https://docs.python.org/3/library/sys.html#sys.setrecursionlimit) |
| P13 | The default limit is 1000; a recursive walk of a 100,000-node path raises `RecursionError` | Run: `memory.py`; quote: [exceptions, `RecursionError`](https://docs.python.org/3/library/exceptions.html#RecursionError) |
| P14 | A default argument value is evaluated only once, so a mutable default is shared between calls | Quote: [tutorial, default argument values](https://docs.python.org/3/tutorial/controlflow.html#default-argument-values) |
| P15 | `insort`: the O(log n) search is dominated by the O(n) insertion step | Quote: [bisect](https://docs.python.org/3/library/bisect.html) |
| P16 | `random()` keeps its sequence for a seed across versions (what makes `balance.py`, `build_cost.py` and `podium.py` deterministic; `shuffle` is not promised, so `balance.py` shuffles with `random()` itself) | Quote: [random](https://docs.python.org/3/library/random.html) |

## Java

| # | Claim | Source |
|---|-------|--------|
| J1 | `PriorityQueue`: an unbounded priority queue based on a priority heap; natural ordering or a `Comparator`; the head is the least element, ties broken arbitrarily; the iterator follows no particular order; O(log n) `offer`, `poll`, `remove()`, `add`; linear `remove(Object)` and `contains`; constant `peek`, `element`, `size`; not synchronized, use `PriorityBlockingQueue` | Quote: [PriorityQueue, Java 21](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/PriorityQueue.html) |
| J2 | `Comparator.reverseOrder()` imposes the reverse of the natural ordering | Quote: [Comparator, Java 21](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Comparator.html) |
| J3 | `TreeMap`: a red-black tree based `NavigableMap`; guaranteed log(n) `containsKey`, `get`, `put`, `remove`; algorithms adapted from Cormen, Leiserson and Rivest; ordering must be consistent with `equals` to behave as a `Map` | Quote: [TreeMap, Java 21](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/TreeMap.html) |
| J4 | `floorKey` returns the greatest key less than or equal to the given key, `ceilingKey` the least key greater than or equal, `subMap` a view of a key range | Quote: TreeMap, Java 21 |
| J5 | OpenJDK's `TreeMap` has `rotateLeft`, `rotateRight`, `fixAfterInsertion` and `fixAfterDeletion`, each marked "From CLR"; the fix-ups recolour (`setColor`) and rotate | Quote: [OpenJDK `TreeMap.java`](https://github.com/openjdk/jdk/blob/master/src/java.base/share/classes/java/util/TreeMap.java) |
| J6 | `ArrayDeque` is likely faster than `Stack` used as a stack and than `LinkedList` used as a queue; `Stack`'s own documentation recommends `Deque` instead | Quote: [ArrayDeque](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/ArrayDeque.html), [Stack](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Stack.html), Java 21 |
| J7 | `StackOverflowError` is thrown when a stack overflow occurs because an application recurses too deeply | Quote: [StackOverflowError, Java 21](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/StackOverflowError.html) |

## Go, Rust and JavaScript

| # | Claim | Source |
|---|-------|--------|
| G1 | `container/heap`: `heap.Interface` is `sort.Interface` plus `Push` (add at index `Len()`) and `Pop` (remove index `Len() - 1`), which are for the package to call; use `heap.Push` and `heap.Pop`; a min-heap with the minimum at index 0; `Init` O(n); `Push`, `Pop`, `Fix` and `Remove` O(log n); `Fix` after the element at index i changed; ordering by the negative priority pops the highest first | Quote: [container/heap](https://pkg.go.dev/container/heap) |
| R1 | `BinaryHeap` is a max-heap; `Reverse` or a custom `Ord` makes a min-heap; push has expected cost O(1) averaged over every ordering, and O(log n) amortized when pushed in ascending order; pop O(log n); peek O(1); converting a `Vec` happens in place in O(n); changing an item's ordering while it is in the heap is a logic error | Quote: [BinaryHeap](https://doc.rust-lang.org/std/collections/struct.BinaryHeap.html); run: `build_cost.py` (1.24 and 1.28 swaps per random push) |
| R2 | `BTreeMap` is an ordered map based on a B-tree; a binary tree allocates per insertion and risks a cache miss per comparison; each B-tree node holds B − 1 to 2B − 1 elements in a contiguous array, cutting allocations by a factor of B; the node search is linear, about B·log(n) comparisons, "generally worse than a BST", yet "performance is excellent"; iteration is in key order; modifying a key's ordering is a logic error | Quote: [BTreeMap](https://doc.rust-lang.org/std/collections/struct.BTreeMap.html), section "Background" |
| JS1 | JavaScript's standard built-in objects include no heap or priority queue: the collections are `Array`, the typed arrays, `Map`, `Set`, `WeakMap` and `WeakSet` | Quote: [MDN, Standard built-in objects](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects) (the page text contains neither "heap" nor "priority") |

## Definitions, history and arithmetic

| # | Claim | Source |
|---|-------|--------|
| D1 | Tree, binary tree (formally: empty, or a root with a left and a right binary tree), depth (root 0, one more than the parent), height (the largest depth; 0 for one node; undefined for an empty tree), full, complete, perfect (2^(h+1) − 1 nodes; in an array, children at 2i and 2i + 1 and parent at i / 2, from 1), binary search tree | Quote: NIST DADS, [tree](https://xlinux.nist.gov/dads/HTML/tree.html), [binary tree](https://xlinux.nist.gov/dads/HTML/binarytree.html), [depth](https://xlinux.nist.gov/dads/HTML/depth.html), [height](https://xlinux.nist.gov/dads/HTML/height.html), [full](https://xlinux.nist.gov/dads/HTML/fullBinaryTree.html), [complete](https://xlinux.nist.gov/dads/HTML/completeBinaryTree.html), [perfect](https://xlinux.nist.gov/dads/HTML/perfectBinaryTree.html), [BST](https://xlinux.nist.gov/dads/HTML/binarySearchTree.html) |
| D2 | The catalog's tree problems count depth and height in nodes (an empty tree 0, one node 1) | Quote: the statements of `max-depth-binary-tree` and `balanced-binary-tree` |
| H1 | J. W. J. Williams, "Algorithm 232: Heapsort", *Communications of the ACM* 7(6), 347–348, June 1964, DOI 10.1145/512274.3734138 | Crossref: [the record](https://api.crossref.org/works/10.1145/512274.3734138). The DOI 10.1145/512274.512284, given by some secondary sources, is Crossref's record for "Algorithm 230: Matrix Permutation" (J. Boothroyd) on the same page; the guide uses the Crossref one |
| H2 | Williams's text: elements 1 to n arranged with each element at most its children at 2i and 2i + 1, "Such an arrangement will be called a heap", the first element always the least; procedures SETHEAP (built by repeated INHEAP), INHEAP, OUTHEAP and SWOPHEAP; INHEAP's loop "may be repeated log_2 n times, but on average is repeated twice only"; uses: sorting, replacement-selection sorting, and "choosing the current minimum of any set of items to which new items are added from time to time" | Read in an ALGOL 60 [transcription](https://www.gtoal.com/languages/algol60/TESTS/a232.a60.html), distributed as a test of the MARST translator; the ACM Digital Library refused the request (HTTP 403). A reviewer with ACM access should compare it with the original |
| A1 | A perfect tree of height h has 2^h leaves and 2^(h+1) − 1 nodes; n nodes need height at least floor(log2 n) and at most n − 1 | Reasoning; run: `shapes.py` |
| A2 | 0-based array layout: children 2i + 1 and 2i + 2, parent (i − 1) // 2, depth floor(log2(i + 1)); level d starts at index 2^d − 1 | Reasoning; run: `array_layout.py`; quote: heapq (P1) |
| A3 | A tree with n nodes has n − 1 edges | Reasoning: one edge per non-root node to its parent |
| A4 | Heapify makes at most the sum of the nodes' heights in swaps, which is below n: the series 1/4 · 1 + 1/8 · 2 + 1/16 · 3 + ... equals 1 | Reasoning (regrouped geometric series); run: `build_cost.py` (sums of heights 994 for 1,000 nodes and 99,994 for 100,000; heapify of descending input 992 and 99,990 swaps) |
| A5 | n pushes of decreasing input cost O(n log n): 7,987 swaps for 1,000 and 1,468,946 for 100,000 | Reasoning; run: `build_cost.py` |
| A6 | The traversal orders of the guide's tree: pre `A B D E H C F G`, in `D B H E A F C G`, post `D H E B F G C A`, level `A B C D E F G H`; stack and recursive versions agree | Run: `traversals.py` |
| A7 | A path of 100,000 nodes: stack peak 200,001 entries; a perfect tree of height 16 (131,071 nodes): stack peak 35, queue peak 65,536 | Run: `memory.py` |
| A8 | The expression `(7 - 2) * (1 + 3) - (6 - 1)` evaluates to 15 in five post-order steps, and prints with exactly those parentheses; `3 - 1` prints as `8 + 3 - 1`, `8 - (3 - 1)` and `8 * (3 - 1)` under its three parents | Run: `expression_tree.py`, checked by Python's own parser |
| A9 | The BST of 41, 20, 65, 11, 29, 50, 91, 32, 72, 99: search paths, floor(55) = 50, and the three delete cases | Run: `bst.py` |
| A10 | 1,000 keys: height 999 sorted, 24 shuffled, best 9; 100,000 shuffled: 40, best 16; averages 500.5, 11.9 and 21.2 comparisons; both shuffled heights are about 2.4 log2 n | Run: `balance.py`; arithmetic |
| A11 | A rotation changes three links and keeps the in-order sequence A, x, B, y, C | Reasoning |
| A12 | A breadth-first walk reaches nodes in order of their number of edges from the start | Reasoning: nothing waiting in the queue is farther than what joins behind it |

## Left out

| What | Why |
|------|-----|
| Robert W. Floyd, "Algorithm 245: Treesort", *CACM* 7(12), 701, December 1964, DOI 10.1145/355588.365103 (Crossref; Crossref's title has no "3") | Its text could not be read: the ACM Digital Library refused the request and no transcription was found. So the guides attribute nothing to it, in particular not the linear-time construction, which the heaps guide proves itself and cites from Python, Go and Rust instead |
| The expected height of a random BST as a theorem | No source read; the guide reports only the measured heights (A10) |
| AVL trees, splay trees, treaps and other balanced designs by name | Only red-black trees (J3, J5) and B-trees (R2) are documented in the libraries cited |
| Approximate quantile summaries for streams | No source read |
| Quickselect, `heapq.merge`, `heapq.nlargest` and `nsmallest` by name, Morris traversal, order-statistic trees, Euler tours | Each answers a hint, an approach or a follow-up of a linked problem (see the spoiler check) |

## Problems on the path, and the ones left out

The path takes 28 of the 41 problems whose `patterns` include `trees`, `heap` or `tries`, from easiest to hardest within each guide, with the hard ones of both halves at the end: `max-path-sum`, `serialize-binary-tree`, `merge-k-sorted-lists`, `median-data-stream`, `maximize-capital` and the four-level `scheduled-transfers-bank`.

| Left out | Why |
|----------|-----|
| `implement-trie`, `wildcard-word-dictionary`, `search-suggestions`, `word-search-ii`, `replace-words` (`tries`) | Tries are trees, but these problems are about string prefixes, and three of them pair the trie with backtracking or binary search. They fit a later guide on tries, in a path on strings and searching, better than a sixth guide here; this path does not mention tries, so that guide will not duplicate anything |
| `time-to-inform-employees` (`graphs`, `trees`) | A graph problem first; and its hints are a child list built from a parent array and the elapsed time carried down, the very tools these guides teach |
| `vertical-order-traversal` (`trees`, `arrays-hashing`) | Its core is grouping and sorting by column; a candidate for `tree-traversals` once it has its own spoiler check |
| `min-meeting-rooms`, `min-interval-per-query`, `employee-free-time` (`intervals`, `heap`) | They belong with the intervals material |
| `network-delay-time`, `swim-rising-water` (`advanced-graphs`, `heap`) | They need shortest paths, which a graphs path teaches |
| `cosine-top-k` (`heap`) | A fourth top-k problem on a bounded heap; three are enough here |

## Spoiler check

Every worked example, trap and note was read against each linked problem's statement, hints, approaches (`solutions/explanation.md`) and follow-ups. The brief for these guides names some techniques that are also hints of the problems that practise them: "in-order gives sorted order", "level order with a queue", "the top-k pattern with a bounded heap" and "two heaps for a running median". The guides teach those on their own examples, as the brief asks, and stop there; the table says, for each problem, what the guides state that overlaps it and what they keep back.

| Problem | Guide | Overlap the guides state | Kept back |
|---------|-------|--------------------------|-----------|
| `invert-binary-tree` | tree-traversals | The tools of follow-up 1 and hint 3: walks with an explicit stack or a queue, and a 100,000-node path that breaks recursion. "Creating a copy of a tree" appears as a use of pre-order (follow-up 3 asks for a mirrored copy) | Swapping children, mirroring, the symmetry check, what a copy costs |
| `level-order-traversal` | tree-traversals | Hint 1: a queue visits nodes level by level (named in the brief). The queue trace shows one level alone in the queue after steps 1 and 3, without remark | Hint 2, reading the queue's size to find a level's end; hint 3, a depth-first walk carrying the depth; every follow-up. All examples print one flat sequence |
| `right-side-view` | tree-traversals | Level order as a flat walk; the recursion guide's remark that a question about levels is often more direct with a level-order walk | Hints 1 to 3: the last node per level, right-first depth-first walks, comparing depth with the answer's length |
| `max-depth-binary-tree` | recursion-on-trees | The definitions of depth and height (trees guide), the note that problems count nodes, structural recursion in general | Hint 1's formula; no code anywhere computes the height of a given tree (`balance.py` records insertion depths of a BST it builds); hint 3, counting levels with a queue; follow-up 2, the minimum depth |
| `same-tree` | recursion-on-trees | Structural recursion in general | Comparing two trees, the null cases, the stack of pairs, both follow-ups |
| `subtree-of-another-tree` | recursion-on-trees | none | Hints 1 to 3: the same-tree test at every node, pre-order with markers, KMP. A note listing an expression tree's pre-order and post-order strings was cut, because it touched what a walk must record to describe a tree |
| `balanced-binary-tree` | recursion-on-trees | Hint 2 in general terms: values travel up in post-order, one walk should return what the parent needs, possibly as a tuple, and a helper walking each subtree from every node costs O(n²) (the same notes overlap follow-up 1). A reader who knows the height formula can go straight from these notes to hint 2's single walk | Hint 1's height helper, hint 3's sentinel, any height code |
| `diameter-binary-tree` | recursion-on-trees | The same general notes as above (follow-up 1) | Hints 1 to 3: the turning node, the sum of two heights, returning one value while recording another |
| `lowest-common-ancestor` | recursion-on-trees | Parent links as a way to store a tree (trees guide). The floor walk of the BST guide walks one path with a candidate, a different question from follow-up 1 | Paths from the root, asking subtrees what they found, returning the found node, the parent map |
| `tree-path-sum-count` | recursion-on-trees | State passed down in general | Prefix sums on the root path, the hash map, adding and removing on the way back; the guide's downward state is an operator and a side, never a sum, never shared and mutated. The guide does not list the prefix-sums guide as related, since that would point at the approach |
| `tree-from-preorder-inorder` | recursion-on-trees | The definitions of pre-order and in-order, under which the root comes first in pre-order | Hints 1 to 3: finding the root in in-order, the split sizes, the index map and cursor; the guides never say that two walks determine a tree |
| `org-chart-outline` | tree-traversals, recursion-on-trees | The statement already explains child lists from parent links. Tools of hint 6 and level 4: an explicit stack that pushes children in reverse so that the first comes off first (for a binary tree, right then left), and the 100,000-deep recursion failure; the note that an iterative values-up walk needs a place for each child's result | Hint 6's (id, depth) pairs and the outline itself, hint 7's sizes from a reversed queue, hint 4's attachment and cycle search, hint 5's chains and common manager. No example computes subtree sizes |
| `max-path-sum` | recursion-on-trees | The general notes on one walk and recomputation (follow-up 1) | Hints 1 to 3: the turning node, gains clipped at zero, the recorded best |
| `serialize-binary-tree` | recursion-on-trees | Pre-order and level order as walks. The idea behind hints 1 and 2, in pictures: the trees guide's definition says that a lone child on the left and a lone child on the right make different binary trees, and every drawing of the path shows a missing child as a box marked "none" so that a lone child keeps its side | Hints 1 to 3 as stated: that a bare pre-order is ambiguous, that a walk or a string must record the missing children, decoding with the same recursion, delimiters. The examples skip empty children silently, and `bst.py` prints no tree shape. The trap "Losing the side of a child" (a list of children loses the side of a lone child) was cut |
| `validate-bst` | binary-search-trees | The ordering invariant over whole subtrees, as the statement words it. Hint 3's first half: in-order lists a BST's keys in increasing order (named in the brief) | Hint 1 as a trap (checking only the children); hint 2's bounds passed down (the recursion guide avoids "limits from ancestors"); hint 3's converse and the previous-value check; the subtree extremes (no example returns a minimum or maximum) |
| `kth-smallest-in-bst` | binary-search-trees | Hint 1 and the first half of hint 2: in-order is sorted (named in the brief) | Counting to k, the early stop, the left-spine stack of hint 3 (the guides' explicit stack uses a different form, a plan pushed in reverse), follow-up 2's sizes in each node |
| `bst-iterator` | binary-search-trees | Hint 1: in-order is sorted. Deletion finds a successor by going right once and then left as far as possible, the same move a step of the iterator makes | Hints 2 and 3: pausing the walk between calls, the left spine as state, `hasNext`; no example uses a generator |
| `last-stone-weight` | heaps | Hint 3's facts as language facts: a heap's costs, and how each language gets a max-heap (Python 3.14's `_max` functions or negated numbers, `Comparator.reverseOrder()`, Rust's default) | The game loop; follow-up 1's cost of re-sorting each round; follow-up 3's counting |
| `single-threaded-cpu` | heaps | Hint 2's shape: a tuple with a tie-breaker (from the `heapq` documentation; the problem's statement fixes the index as the tie-breaker); heaps for schedulers, as `heapq` describes | Hints 1 and 3: feeding tasks by arrival time, the pointer, jumping the clock |
| `task-scheduler` | heaps | none | The counts, the greedy rule, the cooldown queue, the frame formula |
| `kth-largest-element` | heap-patterns | Hints 1 and 2: the bounded min-heap with the item to beat at the root (named in the brief, and already taught by `counting-and-frequency`). The guide calls the root "the smallest of the items kept so far" and its trace prints "the lightest kept weighs ...": once the reader sees that the kept items are the k largest, the answer is the root. With the brief's topic, the problem is close to a recall exercise of this pattern | Saying that the root is the k-th largest (the wording "the weakest member of the current top k" was cut); hint 3's quickselect, never named; follow-ups 2 and 3 |
| `k-closest-points` | heap-patterns | Hint 2 in general: "to keep the k smallest, turn every comparison around"; follow-up 3 in general, since a bounded heap works on a stream | Hint 1's squared distances; hint 3's quickselect |
| `top-k-frequent-elements` | heap-patterns | Hint 2, the bounded heap, already taught by `counting-and-frequency` | Hints 1 and 3 belong to `counting-and-frequency` and are not repeated |
| `design-twitter` | heap-patterns | none | Hints 1 to 3; a "When to use it" line about a heap holding one candidate per sorted source was cut |
| `merge-k-sorted-lists` | heap-patterns | The practice line asks for "well under k comparisons per node", which points at a log k cost, as the problem's statement itself does ("close to log k instead of k") | Hints 1 to 3; the line above was cut, and `heapq.merge` is never mentioned |
| `median-data-stream` | heap-patterns | Hints 1 and 2: the lower half in a max-heap, the upper half in a min-heap, and the middle values at the two roots (named in the brief), shown on one example state, with O(1) reads and an O(log n) arrival in the complexity table (follow-up 2 in general) | Hint 3: neither of its two conditions is stated as a rule (the size balance and the order across the split were cut, along with a 9-to-1 percentile ratio that restated the first), nor the step that sends each arrival through one heap into the other, nor any procedure for an arrival. The `heapq` page's "Other Applications" holds a complete running median: the heaps and heap-patterns guides warn the reader to try the problem first |
| `maximize-capital` | heap-patterns | none | Hints 1 to 3; the line about items becoming available over time was cut |
| `scheduled-transfers-bank` | heap-patterns | Hint 2's shape: a min-heap with a tie-breaking counter (heaps guide, from `heapq`'s documentation). Go's `heap.Remove(h, i)` as an API fact. The heaps guide's table of a sorted list's O(n) insertion touches follow-up 3 | Hint 3, marking cancelled entries and discarding them at the top, which `heapq`'s "Priority Queue Implementation Notes" show: the heaps guide warns the reader to try the problem first; the merges and balance history of hint 4 |

## Changes from the first accuracy review (2026-11-12)

The review found no teaching or factual errors; both Crossref DOIs and the quotes of Williams's text checked out. These are its findings and what changed.

| Finding | Change |
|---------|--------|
| Terminal text drawings put children under the wrong parent: in the trees guide, E's children read as D's; after the rotation, B and C read as A's; the first BST and the expression tree had the same problem | Every tree drawing is now a top-down subgraph inside a left-to-right flowchart. The text renderer then places each parent's first child directly below it and draws every other child with a connector of its own from its parent, instead of one shared bar per level. The rotation's subtrees carry their place in their labels ("B: right of x", "B: left of y"), because there B is the point |
| A lone child lost its side | Every drawing with a lone child marks the empty place with a box labelled "none": the worked-example tree, the complete tree of ten, the traversal tree, both BST trees, the heap of six and the upper half of the two heaps |
| The two-heaps section stated hint 3's two conditions of `median-data-stream` | Cut to the bare idea: the two halves, the middle at the roots, read on one example; the rules, the arrival procedure and the 9-to-1 percentile ratio are gone. The table's row records what remains |
| "The weakest member of the current top k" named the answer of `kth-largest-element` | Now "the smallest of the items kept so far"; the row records the remaining overlap as close to a recall exercise |
| The trees guide's drawing note and its trap "Losing the side of a child" gave the idea behind `serialize-binary-tree`'s hints 1 and 2 | The trap was cut; the drawing note and the "none" boxes remain and are disclosed in the row |
| `balanced-binary-tree` hint 2 and the `merge-k-sorted-lists` log k pointer were not recorded | Both rows now record them |

The text renderer still places nodes on a grid, one column per node, so a second child can stand directly below its parent's right-hand sibling. It is joined to its own parent by a connector, and the sibling shows none, so the drawings read correctly by their lines; the SVG drawings, which the page shows, are laid out as true trees.
