# Review: the facts of the graph guides

The six guides of the path "Graphs: traversal, connectivity and ordering" ([guides](../specs/guides.md), [ADR 0025](../decisions/0025-concept-guides-and-learning-paths.md)) state facts about papers, languages and libraries, and prove a few results in plain language. This page lists each one with where it was checked, so that a later review starts from the sources, and lists what was left out and why.

"Quote" means the exact text was read on that page. "Run" means an example of the guide, or a one-off program, printed it: on CPython 3.13.12, Node.js 24.18.0 and Go 1.27.3. "Proof" means the guide proves it in plain language and the proof should be read for gaps. A fact that could not be checked was left out of the guides.

## Papers

Each paper was found by its DOI in Crossref (`api.crossref.org/works/<doi>`), and its abstract read through OpenAlex (`api.openalex.org/works/doi:<doi>`), which carries the publisher's abstract, unless the row names another source. Only what the named source says is claimed.

| # | Claim | Source |
|---|-------|--------|
| A1 | Lee (1961), "An Algorithm for Path Connections and Its Applications", IEEE Transactions on Electronic Computers EC-10(3), 346–365: path-connection problems in logical drawing, wiring diagramming and optimal route finding; the minimal-distance solution programmed on an IBM 704 | Crossref, [10.1109/TEC.1961.5219222](https://doi.org/10.1109/TEC.1961.5219222); quote: the abstract. The journal's name is Crossref's |
| A2 | Tarjan (1972), "Depth-First Search and Linear Graph Algorithms", SIAM Journal on Computing 1(2), 146–160: illustrates depth-first search with an improved algorithm for strongly connected components and one for biconnected components; time and space bounded by k₁V + k₂E + k₃ | Crossref, [10.1137/0201010](https://doi.org/10.1137/0201010); quote: the abstract, which Crossref carries |
| A3 | Kahn (1962), "Topological Sorting of Large Networks", Communications of the ACM 5(11), 558–562: a very general method for obtaining topological order, required for many problems of network analysis such as PERT; 30,000 activities ordered in less than one hour of machine time, discussed in terms of the 7090; the method had not been programmed and there were no plans to implement it | Crossref, [10.1145/368996.369025](https://doi.org/10.1145/368996.369025); quote: the abstract, which Crossref carries |
| A4 | Galler and Fischer (1964), "An Improved Equivalence Algorithm", Communications of the ACM 7(5), 301–303: storage assignment from EQUIVALENCE declarations with a tree structure, identifying all equivalence classes in one scan | Crossref, [10.1145/364099.364331](https://doi.org/10.1145/364099.364331); quote: the abstract. Crossref spells the second author "Fisher"; OpenAlex and Tarjan's report spell it "Fischer", which the guide uses |
| A5 | Tarjan (1975), "Efficiency of a Good But Not Linear Set Union Algorithm", Journal of the ACM 22(2), 215–225: for m ≥ n finds and n − 1 intermixed unions, k₁ m α(m, n) ≤ t(m, n) ≤ k₂ m α(m, n), α related to a functional inverse of Ackermann's function and very slowly growing | Crossref, [10.1145/321879.321884](https://doi.org/10.1145/321879.321884); quote: the abstract through OpenAlex (OCR'd text, read past its typos) |
| A6 | Tarjan's 1974 report ERL-M434, the same paper's earlier version: sets as trees presented by Galler and Fischer; Knuth attributes the collapsing rule to Tritter; McIlroy and Morris used it independently in an algorithm for spanning trees; Bob Morris apparently first described the weighted union rule; for n finds and n − 1 unions the worst case is of order n² with neither rule, n log n with only one of them (the collapsing-only bounds by Fischer and Paterson), and between k₁ n α(n) and k₂ n α(n) with both, "o(n log* n) but not O(n)"; uses including FORTRAN EQUIVALENCE and COMMON statements, minimum spanning trees, dominators and least common ancestors | Quote: [the report's PDF](https://www2.eecs.berkeley.edu/Pubs/TechRpts/1974/Archive/ERL-m-434.pdf), pages 1 to 4, read as extracted text; the formulas of (1) and (2) are garbled by OCR and were read from their surrounding words and shapes |
| A7 | Tarjan and van Leeuwen (1984), "Worst-case Analysis of Set Union Algorithms", Journal of the ACM 31(2), 245–281: analyses variants of path compression; two one-pass methods proposed by van Leeuwen and van der Weide are asymptotically optimal; several others are slower than the best | Crossref, [10.1145/62.2160](https://doi.org/10.1145/62.2160); quote: the abstract through OpenAlex. The guide's sentence on what "one-pass" means is an explanation of the term, not a quote |
| A8 | Dijkstra (1959), "A Note on Two Problems in Connexion with Graphs", Numerische Mathematik 1, 269–271: n nodes and branches of given length; problem 1, the tree of minimum total length, preferred to Kruskal's and to Loberman and Weinberger's methods, which first sort all of the possibly ½n(n − 1) branches, while it stores at most n branches; problem 2, the path of minimum total length between P and Q, built by constructing minimal paths from P in order of increasing length until Q is reached, with the nodes in three sets A, B and C; remark 1, the process applies when a branch's length depends on its direction | Crossref, [10.1007/BF01386390](https://doi.org/10.1007/BF01386390); quote: the scanned pages 269 and 270 of the Göttingen digitisation, reached from [EuDML 131436](https://eudml.org/doc/131436) |

## Python

| # | Claim | Source |
|---|-------|--------|
| P1 | `defaultdict.__missing__` calls `default_factory`, inserts the value for the key and returns it; it is called only by `__getitem__`, so `get()` does not use it | Quote: [collections, defaultdict](https://docs.python.org/3/library/collections.html#collections.defaultdict); run: `storing_graphs.py` |
| P2 | Changing a dictionary's size while iterating over it raises `RuntimeError: dictionary changed size during iteration`, also when the change is a `defaultdict` read | Run (one-off) |
| P3 | `deque`: thread-safe, memory-efficient appends and pops from either side in approximately O(1); `list.pop(0)` and `list.insert(0, v)` incur O(n) memory movement; indexing O(1) at both ends, O(n) in the middle | Quote: [collections, deque](https://docs.python.org/3/library/collections.html#collections.deque) |
| P4 | `sys.getrecursionlimit()` is the maximum depth of the interpreter stack, which keeps infinite recursion from overflowing the C stack and crashing Python; `setrecursionlimit`'s highest possible value is platform-dependent and a too-high limit can crash; a limit too low for the current depth raises `RecursionError` since 3.5.1 | Quote: [sys](https://docs.python.org/3/library/sys.html#sys.setrecursionlimit) |
| P5 | `RecursionError` derives from `RuntimeError`, added in 3.5; before, a plain `RuntimeError` was raised | Quote: [exceptions](https://docs.python.org/3/library/exceptions.html#RecursionError) |
| P6 | The limit is 1,000 in CPython 3.13; a recursive search from the top level raises `RecursionError` after 999 nodes, the top level taking one frame | Run: `deep_paths.py` |
| P7 | `graphlib` is new in 3.9; `static_order()` raises `CycleError`, a `ValueError` subclass, whose `args[1]` is one cycle with each node an immediate predecessor of the next and the first node repeated last; only one cycle is reported; the order of nodes ready together may depend on insertion order | Quote: [graphlib](https://docs.python.org/3/library/graphlib.html), [What's new in 3.9](https://docs.python.org/3/whatsnew/3.9.html); run: `graphlib_order.py`, the same output under 12 hash seeds |
| P8 | `heapq` is a min-heap with the smallest item at `heap[0]`; tuple comparison breaks for equal priorities whose tasks cannot be compared, and an entry count fixes it; to change a priority, mark the old entry removed and add a new one | Quote: [heapq](https://docs.python.org/3/library/heapq.html) |

## Java, JavaScript and Go

| # | Claim | Source |
|---|-------|--------|
| J1 | `ArrayDeque`: resizable array, no capacity restrictions, not thread-safe, `null` prohibited, likely faster than `Stack` as a stack and than `LinkedList` as a queue; most operations amortized constant time | Quote: [ArrayDeque, Java 21](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/ArrayDeque.html) |
| J2 | `-Xss` sets the thread stack size, rounded up to a page multiple where the OS requires; defaults 1024 KB on Linux/x64 and macOS/x64, 2048 KB on Linux/AArch64 and macOS/AArch64, depending on virtual memory on Windows | Quote: [the `java` command, Java 21](https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html) |
| J3 | `StackOverflowError` is thrown when a stack overflow occurs because an application recurses too deeply | Quote: [StackOverflowError, Java 21](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/StackOverflowError.html) |
| JS1 | The error is `RangeError: Maximum call stack size exceeded` in Chrome, a `RangeError` in Safari, `InternalError: too much recursion` in Firefox | Quote: [MDN, too much recursion](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Errors/Too_much_recursion) |
| JS2 | Node.js 24.18.0 throws `RangeError: Maximum call stack size exceeded` on deep recursion; `node --v8-options` lists `--stack-size` with a default of 984 (KB) | Run (one-off): a recursion one million deep; `node --v8-options` |
| GO1 | `debug.SetMaxStack` sets the most memory a single goroutine stack may use; a goroutine that exceeds it while growing crashes the program; initially 1 GB on 64-bit and 250 MB on 32-bit systems; useful mainly for limiting infinite recursion | Quote: [runtime/debug](https://pkg.go.dev/runtime/debug#SetMaxStack) |
| GO2 | A recursive search 200,000 deep finishes in Go | Run: `deep_paths.go` (about 67 MB resident) |

## Proofs, arithmetic and runs

| # | Claim | Source |
|---|-------|--------|
| M1 | The degrees sum to twice the number of edges; a simple graph has at most V(V − 1)/2 undirected or V(V − 1) directed edges | Proof; run: `storing_graphs.py` (8 = 2 × 4) |
| M2 | BFS records every node at its true distance when all edges count the same; the queue holds at most two neighboring distances, in order | Proof (breadth-first-search, "Why the first discovery is the shortest") |
| M3 | Marking on exit pushes 1 + 29 + 28 + ... + 1 = 436 entries on a club of 30 where everybody knows everybody, against 30 when marking on discovery | Run: `when_to_mark.py`; arithmetic |
| M4 | The jug puzzle needs 6 pours; 14 of the 24 pairs are reachable; after every move one jug is full or empty | Run: `two_jugs.py`; the last by checking the six moves |
| M5 | An edge to a grey node closes a cycle, and every cycle produces such an edge; an undirected DFS has only tree edges and edges back to an ancestor | Proof (depth-first-search) |
| M6 | Union by size keeps every element within log₂ n steps of its root | Proof (union-find); run: `tree_depth.py`, tournament of 1,024 reaches depth 10 |
| M7 | Plain linking of the chain makes a path 1,023 deep, with depths summing to 523,776 = 1,023 · 1,024 / 2; one compressing find of each element flattens the tournament to depth 1 | Run: `tree_depth.py`; arithmetic |
| M8 | A topological order exists exactly when there is no directed cycle; Kahn's algorithm never gets stuck on a DAG; the reversed DFS finish order is an order | Proof (topological-order, "Why it works") |
| M9 | The order is unique exactly when each pair of neighbors in it is joined by an arrow, that is, when Kahn's algorithm never has more than one node ready; the smallest ready node first gives the order first in dictionary order | Proof (topological-order, expert notes) |
| M10 | Dijkstra's algorithm settles each node at its true distance when no edge is negative; one negative edge breaks it (`b` 2 against 1); relaxing every edge V − 1 times finds the truth, and a change in a V-th round means a negative cycle | Proof (weighted-shortest-paths); run: `negative_edge.py`, `cycling_times.py` |
| M11 | With a binary heap and outdated entries skipped, the heap holds at most E + 1 entries and the search costs O((V + E) log V) | Arithmetic: a relaxation only pushes towards an unsettled node, so each edge pushes at most once |
| M12 | Every Python example prints the same output under 12 different hash seeds | Run: all 15 Python examples, with `PYTHONHASHSEED` from 0 to 11 |

## Left out

| What | Why |
|------|-----|
| Moore (1959), "The shortest path through a maze" | No DOI, and no readable copy of the proceedings was found; the BFS history names Lee (1961) only |
| Which one-pass compression methods Tarjan and van Leeuwen proved optimal (path halving, path splitting) | The abstract does not name them, and the ACM full text refused the request (HTTP 403) |
| Kruskal's algorithm skipping edges inside a group | No source read; the guide only says, from Tarjan's report, that set union is used to find minimum spanning trees |
| A `Thread` constructor with a stack size as the Java fix for deep recursion | Not checked against the `Thread` documentation |
| That Python frames live on the C stack | Not true of every version, and not needed: the guide quotes the documentation's warning instead |
| Union by rank, and α(n) ≤ 4 for any practical n | No primary source read |
| The definition of PERT | The abstract names PERT without defining it |
| Multi-source BFS spelled out on a grid, Kahn's algorithm by rounds, 0-1 weights, bottleneck paths, two-colouring and searching from the border | Each would answer a practice problem of the path; see the spoiler check |

## Spoiler check

Each worked example was compared with the statement, the hints and the approaches of the practice problems of its guide and of the path.

| Guide | Worked examples | Closest practice problems, and why it is not their solution |
|-------|-----------------|--------------------------------------------------------------|
| graph-representations | A trail map in three forms; one-way lifts with in-degrees; neighbors of a grid cell | `employee-importance`, `time-to-inform-employees`: neither records nor a manager column are converted; no traversal or sum is shown |
| breadth-first-search | Fewest tram stops with parents; marking on discovery on a complete graph; the two-jug puzzle | `shortest-path-binary-matrix`, `open-the-lock`, `word-ladder`, `shortest-path-with-removals`: no grid, lock or word moves, and the jug state holds no budget; `rotting-oranges`: the expert note on several starts states the technique in one sentence with no example (flag for review: it is close to that problem's second hint); `clone-graph`: no copying |
| depth-first-search | Components of a museum's rooms; three colours on module imports; recursion depth on a path | `number-of-islands`, `max-area-of-island`: adjacency lists, not grids, and no sizes; `contractor-exposure-rollup`: the colour lesson is the one its second hint names, but the example sums nothing and reports the cycle instead of refusing it; `bipartite-graph`, `surrounded-regions`, `pacific-atlantic-water-flow`: not mentioned beyond their questions |
| union-find | Doors opening in a game level, with connectivity questions; tree depths for two union orders | `count-connected-components`, `number-of-islands-ii`: the example never counts groups; `redundant-connection`: "an edge inside one group closes a cycle" is stated, choosing among cycle edges is not; `accounts-merge`, `duplicate-contractor-records`, `smallest-string-with-swaps`, `evaluate-division`, `referral-rewards`: no records, strings, ratios or referrals |
| topological-order | A start order for six services by Kahn's algorithm and DFS, with a cycle; `graphlib` | `course-schedule`, `course-schedule-ii`: the technique is the guide's subject, the input shape and edge direction differ; `parallel-courses`: rounds are not counted; `alien-dictionary`: no edges from words; `all-possible-recipes`: no supplies; `longest-increasing-path-matrix`: no grid and no longest path |
| weighted-shortest-paths | Fastest cycling route to one goal; one negative edge | `network-delay-time`: one target with an early stop, not the latest arrival over all nodes; `min-obstacle-removal`, `swim-rising-water`: no grids, no 0-1 costs, no maximum along a route |
