# Review: the facts of the stacks, queues and tries guides

The five guides of the path "Stacks, queues and tries: from matching pairs to prefix trees" (`guides/paths/stacks-queues-and-tries.yaml`; [guides](../specs/guides.md), [ADR 0025](../decisions/0025-concept-guides-and-learning-paths.md)) state facts about languages, libraries and the history of the ideas. This page lists each one with where it was checked, so that the independent review starts from the sources, and checks every guide against the problems it links for spoilers.

The guides are `stacks`, `evaluating-expressions`, `queues-and-deques`, `monotonic-stacks` and `tries`.

"Quote" means the exact text was read on that page. "Read" means it was read on a scanned page image. "Run" means an example of the guide, or a one-off program, printed it: on CPython 3.13.12 and OpenJDK 21.0.2. A fact that could not be checked was left out of the guides; the last section lists what was left out.

## Python

| # | Claim | Source |
|---|-------|--------|
| P1 | A list is a stack with `append` and `pop()`, last in first out; `pop` raises `IndexError` on an empty list | Quote: [tutorial, using lists as stacks](https://docs.python.org/3/tutorial/datastructures.html#using-lists-as-stacks), `list.pop` in the same page |
| P2 | Lists are "not efficient" as queues: inserts or pops at the beginning are slow "because all of the other elements have to be shifted by one"; use `collections.deque` | Quote: [tutorial, using lists as queues](https://docs.python.org/3/tutorial/datastructures.html#using-lists-as-queues) |
| P3 | `deque` is pronounced "deck", short for double-ended queue; "thread-safe, memory efficient appends and pops from either side ... approximately the same O(1) performance in either direction"; lists "incur O(n) memory movement costs for `pop(0)` and `insert(0, v)`" | Quote: [collections.deque](https://docs.python.org/3/library/collections.html#collections.deque) |
| P4 | Indexed access to a deque "is O(1) at both ends but slows to O(n) in the middle" | Quote: collections.deque |
| P5 | `maxlen`: once a bounded deque is full, adding items discards "a corresponding number of items ... from the opposite end"; compared with the Unix `tail` filter | Quote: collections.deque |
| P6 | `pop` and `popleft` raise `IndexError` on an empty deque | Quote: collections.deque |
| P7 | CPython's deque is "a doubly-linked list of fixed length blocks"; `BLOCKLEN` is 64; blocks mean proportionally fewer calls to `malloc` and `free`, better cache locality, and no `realloc` | Quote: [`Modules/_collectionsmodule.c`](https://github.com/python/cpython/blob/main/Modules/_collectionsmodule.c) |
| P8 | `sys.getrecursionlimit()` is "the maximum depth of the Python interpreter stack"; exceeding it raises `RecursionError`, derived from `RuntimeError`, added in 3.5 | Quote: [sys](https://docs.python.org/3/library/sys.html#sys.getrecursionlimit), [exceptions](https://docs.python.org/3/library/exceptions.html#RecursionError) |
| P9 | The limit is 1000 in a fresh CPython 3.13; 5,000 nested lists raise `RecursionError` recursively and not with an explicit stack | Run: `nesting_depth.py`. The documentation does not state the default, so the guide gives it as what the example prints |
| P10 | `eval` "executes arbitrary code" and calling it with untrusted input "will lead to security vulnerabilities" | Quote: [functions, eval](https://docs.python.org/3/library/functions.html#eval) |
| P11 | `dis` describes the interpreter stack as `STACK`; `BINARY_OP`, added in 3.11, is `rhs = STACK.pop()`, `lhs = STACK.pop()`, `STACK.append(lhs op rhs)` | Quote: [dis](https://docs.python.org/3/library/dis.html#opcode-BINARY_OP) |
| P12 | `|`, `&` and `-` on sets are union, intersection and difference; difference is not symmetric | Run: `postfix_filter.py`, `two_stacks.py` (each checked against a parenthesized Python expression) |
| P13 | `dict.get` and `dict.setdefault` build a trie's children | Run: `commands.py`, `typos.py` |

## Java

| # | Claim | Source |
|---|-------|--------|
| J1 | `Stack` extends `Vector`, since 1.0; `Deque` and its implementations, "a more complete and consistent set of LIFO stack operations", should be used in preference, e.g. `Deque<Integer> stack = new ArrayDeque<Integer>()` | Quote: [Stack, Java 21](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Stack.html); run: `StackOrder.java` (`add(0, "z")` changes the bottom) |
| J2 | `Stack.pop` and `peek` throw `EmptyStackException` on an empty stack | Quote: Stack, Java 21; run: `StackOrder.java` |
| J3 | `ArrayDeque`: "resizable-array implementation", "no capacity restrictions", not thread-safe, null elements prohibited, "likely to be faster than `Stack` when used as a stack, and faster than `LinkedList` when used as a queue", most operations in amortized constant time | Quote: [ArrayDeque, Java 21](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/ArrayDeque.html) |
| J4 | `ArrayDeque.pop` throws `NoSuchElementException` when empty, `peek` and `poll` return `null`; `push` is `addFirst`; `addFirst` and `addLast` throw `NullPointerException` for `null` | Quote: ArrayDeque, Java 21; run: `StackOrder.java` |
| J5 | `ArrayDeque`'s iterator runs from head to tail, "the same order that elements would be ... popped"; a `Stack` lists bottom first, so the two list the same pushes in opposite orders | Quote: ArrayDeque, Java 21; run: `StackOrder.java` |
| J6 | `Deque` as a queue: `add`/`offer` at the end, `remove`/`poll` at the beginning; as a stack: `push`, `pop`, `peek` at the beginning; prefer it to the legacy `Stack`; implementations are encouraged to prohibit `null` because `null` signals an empty deque | Quote: [Deque, Java 21](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Deque.html) |
| J7 | Each JVM frame contains "a last-in-first-out (LIFO) stack known as its operand stack"; `iadd` pops two `int` values and pushes their sum | Quote: [JVMS §2.6.2](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-2.html#jvms-2.6.2) |

## Go, Rust and JavaScript

| # | Claim | Source |
|---|-------|--------|
| G1 | `append` appends to the end of a slice, reslicing when the capacity suffices and allocating a new underlying array when not; its result must be stored | Quote: [builtin append](https://pkg.go.dev/builtin#append) |
| G2 | An index out of range at run time is a run-time panic, so `s[len(s)-1]` on an empty slice panics | Quote: [the Go specification, index expressions](https://go.dev/ref/spec#Index_expressions) |
| G3 | `container/list` "implements a doubly linked list" | Quote: [container/list](https://pkg.go.dev/container/list) |
| G4 | "Re-slicing a slice doesn't make a copy of the underlying array"; "the full array will be kept in memory until it is no longer referenced" | Quote: [Go Slices: usage and internals](https://go.dev/blog/slices-intro) |
| G5 | After `q = q[1:]`, what the dropped items point to stays reachable until `append` next moves the slice to a new array | Reasoning from G1 and G4: the old array stays referenced until a reallocation replaces it |
| R1 | "Use a `Vec<T>` as an efficient stack"; `pop` returns `Option<T>`, `None` when empty, in O(1); `push` takes amortized O(1), the O(capacity) copy "offset by the capacity O(1) insertions it allows" | Quote: [Rust `Vec`](https://doc.rust-lang.org/std/vec/struct.Vec.html) |
| R2 | `VecDeque` is "a double-ended queue implemented with a growable ring buffer"; its default use as a queue is `push_back` and `pop_front`; `pop_front` and `pop_back` return `None` when empty; its elements are not necessarily contiguous, and `make_contiguous` rotates them into one slice | Quote: [Rust `VecDeque`](https://doc.rust-lang.org/std/collections/struct.VecDeque.html) |
| JS1 | `pop()` on an empty array returns `undefined` | Quote: [MDN, Array.prototype.pop](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/pop) |
| JS2 | `shift()` "shifts all values to the left by 1 and decrements the length by 1" | Quote: [MDN, Array.prototype.shift](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/shift). No cost is claimed: MDN states none |

## History and literature

| # | Claim | Source |
|---|-------|--------|
| H1 | Dijkstra, "Making a Translator for ALGOL 60", published in the APIC Bulletin no. 7, May 1961, and reprinted with "An ALGOL 60 Translator for the X1" in "ALGOL-60 Translation", Mathematisch Centrum, November 1961 (ALGOL Bulletin Supplement nr. 10) | Read: [ir.cwi.nl/pub/9251](https://ir.cwi.nl/pub/9251), the cover and the footnote on the first page of the second part (PDF pages 1 and 23) |
| H2 | The operator stack and its priority rule serve a translator, not an evaluator; "the translation process shows much resemblance to shunting at a three way railroad junction", and operators wait in the translator stack | Read: same report, second part, page 7 (PDF page 29) |
| H3 | Operators carry priority numbers; before a new operator enters the translator stack, operators leave it "as long as their priority number is greater then [sic] or equal to" the new one's; an opening bracket enters with priority 0, "shielding all postponed operations"; "the priority numbers in the translator stack increased monotonically" until brackets "interrupt this monotony" | Read: same report, second part, pages 7 and 8 (PDF pages 29 and 30) |
| H4 | The X1 translator's object programs evaluate algebraic expressions "with the help of an accumulator stack", citing K. Samelson and F. L. Bauer, "Sequentielle Formelübersetzung", Elektronische Rechenanlagen 1 (1959) | Read: same report, first part, page 4 and its references, page 20 (PDF pages 6 and 22) |
| H5 | E. Fredkin, "Trie memory", Communications of the ACM 3(9), 490–499, September 1960; the guide says only that the name appears in its title | Quote: [Crossref, 10.1145/367390.367400](https://api.crossref.org/works/10.1145/367390.367400). The paper itself was not readable (HTTP 403) |
| H6 | O. Berkman, B. Schieber and U. Vishkin, "Optimal Doubly Logarithmic Parallel Algorithms Based On Finding All Nearest Smaller Values", Journal of Algorithms 14(3), 344–370, 1993 | Quote: Crossref, 10.1006/jagm.1993.1018. Only the title is used: the problem's name |

## Standard results and arithmetic

| # | Claim | Source |
|---|-------|--------|
| S1 | A queue from two stacks costs at most 4 stack operations per item over its life, so O(1) amortized, while one dequeue can cost O(n); after 100,000 enqueues, the first dequeue does 200,001 operations; moving while the outbox holds items breaks the order | Run: `two_stack_queue.py` (4.00 per item, same order as `collections.deque`, the eager variant serves `a c b`); proof in the guide |
| S2 | A monotonic stack does n pushes and at most n pops; with the size as potential, every arrival costs 2; 2,001 people in a shrinking line take 2,001,000 comparisons by scanning and 4,001 stack operations | Run: `next_taller.py`; arithmetic |
| S3 | The window deque pushes each item once and pops it at most once: 20,000 pushes and 19,997 pops, and the same answers as a scan | Run: `window_minimum.py` |
| S4 | Applying waiting operators of equal precedence groups them left to right; applying only strictly higher ones groups them right to left | Run: `two_stacks.py` (`staff - oncall - away` gives `{bo, di}` and `{bo, di, ed}`) |
| S5 | Postfix lists the expression tree children first, then the node; prefix ("Polish notation") puts the operator first instead of last, and is evaluated right to left, where the first value popped is the left operand; exponentiation groups from the right in mathematics | Standard results and terms, stated without a fetched source |
| S6 | With a budget of one changed letter, the trie walk takes at most about σ · L² steps | Arithmetic: L positions, at most σ − 1 detours each, each followed for at most L letters |
| S7 | A compressed trie (radix tree) has at most about twice as many nodes as keys | Standard result, stated without a fetched source: leaves and marked nodes are at most n, branching nodes fewer than the leaves |
| S8 | 10,000 numbered keys need 11,114 trie nodes for 80,000 letters; 10,000 scattered 8-letter keys need 58,241 | Run: `sharing.py` |
| S9 | A hash set answers "which keys start with this prefix?" only by looking at every key | Reasoning: hashing scatters keys and keeps no order of prefixes (see the hashing guides) |

## Left out

| What | Why |
|------|-----|
| What R. de la Briandais's "File searching using variable length keys" (Western Joint Computer Conference, 1959, pages 295–298) describes | Crossref gives its metadata, but the paper returned HTTP 403, so nothing about its content can be claimed |
| That Fredkin coined the word "trie", or how it is pronounced | The paper could not be read; only its title is used |
| Morrison's PATRICIA (Journal of the ACM, 1968) as the origin of compressed tries | The abstract was reachable but does not say how the structure compresses; compressed tries are described without attribution |
| The cost of JavaScript's `shift` | MDN states none, and the specification defines behaviour, not cost |
| The time complexity of `VecDeque`'s push and pop | The part of the page read states none for them |
| Python's default recursion limit as a documented value | The documentation does not give it; the guide reports what the example prints |
| A sorted array with binary search, and sorted iteration of a trie, as alternatives for prefix questions | Left out on purpose: they are `search-suggestions`'s first approach and hints |

## Spoilers: the practice problems against the guides

Every worked example, trap and note was checked against each linked problem's statement, hints, approaches and follow-ups. The brief asks the guides to teach some techniques that are, by nature, the core of a linked problem (matching pairs with a stack, postfix evaluation, the window deque, next greater with a monotonic stack, trie insert and lookup, counting by prefix, wildcard search by branching). For those, the guides teach the technique on an example from another domain and leave the problem's own shape, traps and follow-ups alone; the rows marked **adjacent** say exactly how close they come, for the reviewer to judge. The first review accepted them all and asked for the softenings listed under its changes below.

| Problem | What the problem itself gives | What the guides teach, and on what | Verdict |
|---------|-------------------------------|------------------------------------|---------|
| `valid-parentheses` | Hints: a stack of openers, the closer matches the top, empty at the end. Follow-ups: one pass; O(1) memory with one bracket kind; the position of the first error | `stacks`: the same top-and-empty rule on a timing trace of named sections. No brackets, no counter for one kind, and its errors name sections, not positions | Adjacent: the technique, by design |
| `generate-parentheses` | Hints: the prefix rule; add `(` while fewer than n; add `)` while it closes something. Follow-ups: a counter instead of a stack; build only valid strings; Catalan numbers | Nothing about generating strings or counting opens | Clear |
| `min-stack` | Hints: the minimum at or below each element; a second stack of minimums, with care for equal values. Follow-ups 1 to 3 | `stacks` tracks no minimum, and no guide describes a minimum kept by a stack. `queues-and-deques` teaches the two-stack queue on its own, and keeps the cheapest offer of a time window with a deque | Accepted on review: the window deque is the brief's technique; the guides use no wording of follow-up 3 |
| `min-remove-to-balance` | Hints: a counter of opens; an unmatched `)` is deleted; positions of unmatched `(` on a stack. Follow-ups: count in one pass; two passes without a stack | The trace checker raises an error; it never collects unmatched items or repairs the input | Clear |
| `decode-string` | Hints: expand innermost groups; on `[` push the count and the text, on `]` pop and repeat. Follow-ups: one pass; a recursive and an iterative version; multi-digit counts | `nesting_depth.py` rewrites a recursive depth measure of nested lists as a loop over an explicit stack. No repetition, no strings, no counts | Adjacent to follow-up 2 in its general form only |
| `valid-parenthesis-string` | Hints: a counter that never goes negative; with wildcards, a range of counts | Nothing about counters, ranges or wildcards | Clear |
| `evaluate-rpn` | Statement: postfix, the earlier operand is the left one. Hints: push numbers, pop two, the first popped is the right operand. Follow-ups: one pass; infix to postfix; validating the tokens | `evaluating-expressions`: postfix evaluation of set filters, with the pop order that the statement already gives, and the two-stack method for infix. The Dijkstra note keeps the attribution, the shunting quote, the priority rule and the monotonic remark, and no longer describes the junction's tracks. No integers, no division rule, no validation | Accepted on review: postfix and two-stack infix are the brief's techniques; follow-up 2 softened by cutting the tracks clause |
| `basic-calculator` | Approaches: reduce and splice; a stack of signed terms; a running total and pending term. Hints: a sum of terms. Follow-ups: one pass without tokenizing; O(1) memory; parentheses | The two-stack method evaluates infix set filters with precedence and parentheses: a general method that would also solve the problem, by a route none of its approaches takes. Signed terms, the pending term and O(1) memory are not mentioned | Accepted on review: the brief's two-stack method |
| `sliding-window-maximum` | Hints: an element with a larger one to its right inside the window is useless; a deque of positions with values decreasing; drop the front when it leaves. Follow-ups: a heap; O(n) with candidates; minimum and maximum at once | `queues-and-deques`: the deque for window extremes, as the brief asks, on the minimum of a time-based window over a stream of offers. No maximum, no positions, no count-based window, no output per window, no flip to the maximum | Adjacent: the technique, by design |
| `daily-temperatures` | Hints: the days still waiting; they never get warmer from oldest to newest; pop and answer every colder day. Follow-ups: one pass; scanning from the last day; the most recent earlier warmer day | `monotonic-stacks`: the first strictly taller person in front, in a line of people, with the invariant the brief asks for. Nothing about scanning backwards or about earlier items | Adjacent: the technique, by design |
| `stock-span` | Hints: forget days that cannot stop a walk; a decreasing stack; absorb a popped entry's span. Follow-ups: O(1) amortized; strictly lower prices | No question about earlier items; nothing is absorbed or merged on pop | Clear |
| `car-fleet` | Hints: arrival times; process from the car closest to the target; a stack of fleet arrival times. Follow-ups: sorting order; integers only; counting sort | Nothing about sorting, times or fleets | Clear |
| `remove-k-digits` | Hints: delete the first digit larger than the next; pop while deletions remain; spend the rest at the end; strip zeros. Follow-ups | No popping budget, no smallest number | Clear |
| `sum-of-subarray-minimums` | Hints: a contribution of `left * right`; previous and next smaller elements; break ties on one side only. Follow-ups: per-element counts; which copy of a tie counts; sums of maximums | The next shorter person, by flipping the comparison, in one line of output; the equal-values trap covers the guide's own question only. Nothing about counting subarrays, previous smaller elements or attributing ties | Adjacent, lightly |
| `trapping-rain-water` | Hints: the water level is the smaller of two maxima; prefix maxima; two pointers | Nothing about water, maxima or two pointers | Clear |
| `largest-rectangle-histogram` | Hints: the lowest bar and its two boundaries; a stack of bar indexes; the bar below a popped one is its left boundary; a final 0 flushes the stack. Follow-ups: nearest lower bar on each side in one pass | Nothing about the item below a popped one, both sides, widths or a sentinel. The literature note gives only the name "all nearest smaller values" | Clear |
| `maximal-rectangle` | Hints: a histogram per row; updating heights; boundaries per column | The practice line names the question only | Clear |
| `implement-trie` | Hints: a set makes `startsWith` slow; one child per letter and an end flag; search and `startsWith` differ only at the end. Follow-ups: an alphabet as large as Unicode; counting words under a prefix without walking them | `tries`: insert, lookup and the end mark, as the brief asks, on command names. Its per-node counts are the brief's "counting by prefix", now described without the follow-up's wording about not walking what lies below. The note on children says only that their layout is the main memory lever and what a map per node costs | Accepted on review: the trie and its counts are the brief's techniques; follow-up 1 removed by cutting the array and list comparison |
| `replace-words` | Hints: only prefixes of the word matter; walk a trie of roots and stop at the first end. Follow-ups: a set of roots and a check of each prefix of a word; roots inside words | Resolving an abbreviation walks what was typed through the stored names; no query asks which stored key is a prefix of a string. The hash set comparison is about keys that start with a prefix, the other direction | Clear |
| `wildcard-word-dictionary` | Hints: at a dot, try every child; a depth-first search by position; check the end flag. Follow-ups: the cost with many dots; a `*` wildcard | `tries`: branching search with a budget of one changed letter, as the brief asks, for typo suggestions; the same depth-first shape. No dots, no `*`; its cost is stated for one change only | Adjacent: the technique, by design |
| `search-suggestions` | Hints: sort and binary-search the block of a prefix; trie nodes keep their three smallest products. Follow-ups: narrowing from a shorter prefix; products added while typing | No sorted array, no binary search, no sorted enumeration and no top-k lists in nodes; the counts per node are a different summary | Clear, with the sorted alternative left out on purpose |
| `word-search-ii` | Hints: a depth-first search per word; walk the board and the trie together and prune; store the word at its end node and clear it once found | No grids. "One walk prunes every key that cannot match" in the trie's uses is general; the example stores a summary at the end node, not the key | Clear |

Examples were also checked against the rest of the catalog, so that none teaches on another problem: the trie uses command names, not path segments, because `api-gateway` routes with a trie of path segments and `authorization-policy-engine` matches resource paths; the editor's undo is not a nested transaction log, which is `transactional-kv-store`; and `cloud-file-storage` asks for files by prefix, which the counts per node do not answer.

## Changes from the first accuracy review (2026-11-12)

The review re-fetched every source and found no factual errors and no wrong algorithms; all 12 examples print what their guides say. It accepted the techniques the brief names (postfix, two-stack infix, the trie and its counts) and asked for these changes.

| Finding | Change |
|---------|--------|
| "Postfix is its reverse" is false: reversing a postfix expression swaps the operands | Prefix order now "puts the operator first instead of last" |
| Dijkstra's report describes translating to reverse Polish, not evaluating | "The operator stack and its priority rule come from" the report, "where they serve a translator rather than an evaluator"; the heading says where the operator stack comes from |
| The junction's three tracks, input, output and stack, spelled out infix to postfix: `evaluate-rpn` follow-up 2 in prose | The tracks clause is cut; the attribution, the shunting quote, the priority rule and the monotonic remark stay |
| The comparison of a map, an array and a sorted list for a node's children answered `implement-trie` follow-up 1 | The note keeps only that the children's layout is the main memory lever, and what a map per node costs |
| Two sentences on counting by prefix echoed `implement-trie` follow-up 2 | "One step per letter of the prefix" in the guide; "the count of the prefix's last node" in `commands.py`; the complexity row no longer mentions visiting the keys below |
| The trie drawing fanned out from a box with no exit connector | One row for the shared path and one row for each branch below `g`, 69 characters wide |
| No blank line before "What to use instead" in `monotonic-stacks` | Added |
| `queues-and-deques` said it "builds or draws" all three queue designs | It builds the first, draws the second and describes the third |
| `trie` note named `d` as a node with a single child | `d` is a leaf: the note names the `i` and the `l` that lead to it |
| "Amortized" appeared in the stacks guide before it is explained | The `ArrayDeque` clause no longer uses the word |
| The ring buffer drawing showed only queue order | It lists the array in slot order, with the front, the back, the next free slot and the wrap |
| "The graphs path covers it" refers to a path on another branch | Dropped |

## Choices for the reviewer

| Choice | Why |
|--------|-----|
| Five guides: expression evaluation is a guide of its own | The brief puts it under stacks; with matching pairs, undo and recursion, one guide would have been twice the length of any hashing guide |
| `queues-and-deques` comes before `monotonic-stacks`, and its only practice problem sits in the closing block | Queues are introductory; the window deque motivates the monotonic stack, which then generalizes it. `sliding-window-maximum` is hard, so it closes the path |
| `bst-iterator` (patterns `trees`, `stack`) is not in the path | It needs the binary search tree guide of the trees path |
| `generate-parentheses` (patterns `backtracking`, `stack`) is in the path | No other path covers it, and its rule is the nesting rule of the stacks guide |
| `trapping-rain-water` and `sliding-window-maximum` gain `guides` lines here and on the two-pointers branch | The two branches will conflict on those two lines; the merge keeps both guides in one list |
