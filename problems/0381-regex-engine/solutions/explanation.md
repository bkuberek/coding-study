# Regex Engine: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| thompson-simulation | optimal | O(m) to parse and build; O(n m) per match, count or search | O(m) | default answer; the same automaton serves matching, counting and searching |

Here `m` is the length of the pattern and `n` the length of the text.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | A recursive-descent parser, one function per grammar rule, and a printer for the tree | the tree: tuples or small node objects for `lit`, `any`, `empty`, `cat`, `alt`, `star`, `plus`, `opt` |
| 2 | Thompson's construction over the tree, then a breadth-first renumbering | an automaton: for each state its kind, its label and its list of arrows |
| 3 | A closure with a stack and a seen set; one set of states per character | nothing new: matching and counting are two readings of one run |
| 4 | Classes as a new atom and a new kind of state; a leftmost-longest search | the class items on the state; the search reuses the closure and the step |

The early choice that keeps the later levels cheap is to keep the three stages apart: the tree knows nothing about states, and the automaton knows nothing about the pattern's text. Level 4 then adds one atom to the parser, one kind of state to the construction and one test to the step, and none of the earlier code changes.

## Approach: thompson-simulation (Recursive descent, Thompson's construction and a state-set simulation)

### Intuition

A regular expression is a small program, so an engine treats it like one: parse it, translate it, run it. The grammar has one rule per precedence level, and a parser with one function per rule gets the precedence right by construction. The tree then translates node by node into a fragment of an automaton with loose arrows, and gluing fragments is filling in loose arrows. Running a nondeterministic automaton by trying one path at a time means going back when it fails, which can take exponentially many tries; keeping the set of all the states it could be in instead costs at most one visit per state per character, because a state is in the set or not, however many paths lead to it.

### Algorithm

1. Level 1: `alternation` reads `sequence`s separated by `|`; `sequence` reads `repetition`s until `|`, `)` or the end; `repetition` reads an `atom` and wraps it once per following `*`, `+` or `?`; `atom` reads a literal, `.`, or a group, which recursively reads an `alternation` and then expects `)`. One-element sequences and one-sided alternations collapse to their only child, and an empty sequence becomes `empty`. Errors are raised where they are found: a repetition operator where an atom should begin, a `)` left after the top-level `alternation`, the end of the pattern inside a group.
2. Level 2: `fragment(node)` returns a start state and a list of loose arrows, each a (state, arrow index) pair. Leaves create one state with one loose arrow; `cat` points each child's loose arrows at the next child's start; `alt` creates a `split` with one arrow per side; `star`, `plus` and `opt` create a two-arrow `split` whose first arrow enters the child and differ only in which state is the start and where the child's loose arrows point. A final `match` state receives the remaining loose arrows. A queue from the start then renumbers the states breadth first.
3. Level 3: `closure(sources)` pops states from a stack, skips those already reached, records the others and pushes the targets of `split` and `empty` states. The run starts from `closure({0})`; each character keeps the arrows of the states that accept it and closes their targets. The run stops early on an empty set; `fullMatch` asks whether the last set holds the match state and `countSteps` sums the sizes of the sets.
4. Level 4: a `[` starts a class: an optional `^`, then items until `]`, where an item is a range when a `-` follows it and the character after the `-` is not `]`. A class state accepts a character when the character lies in one of the item ranges, inverted for a negated class. `search` runs one pass: every live state carries the earliest start that reaches it, kept in a list ordered by start. Until a match has been seen, each position adds the closure of the start state with that position as its start. When the match state is live, its start and the current position are the best match so far; states with a later start are dropped, and the scan goes on while any state is live.

### Correctness

Parser: each function returns exactly the tree of the longest text that its rule can derive from the current position, and it stops at the first character that its rule cannot continue with. Repetition binds to one atom because only `repetition` reads the operators and it has read one atom; concatenation binds tighter than alternation because `sequence` never consumes `|`. The first error in reading order is the first point at which no rule can continue, which is where the code raises it; an open group can only be detected at the end of the pattern, and the innermost one detects it first because it is the active call.

Construction: by induction on the tree, the fragment of a node accepts, from its start state through its loose arrows, exactly the strings of that node. For `star(X)`, the `split` either leaves (zero repetitions) or enters `X`, whose end returns to the `split`, so any number of repetitions is possible; `plus(X)` starts inside `X`, so at least one is required; `opt(X)` either enters `X` once or leaves. Breadth-first numbering depends only on the graph and the order of the arrows, so it is the same however the states were created.

Simulation: by induction on the number of characters read, the set after `i` characters is exactly the set of states that some path reaches after reading the first `i` characters, followed by silent arrows. The closure adds every state reachable by silent arrows, and the step adds every target of an accepted character, so nothing is missed; nothing else is added. The text matches exactly when a path reaches the match state after the last character, which is when the last set holds it. An empty set can only lead to empty sets, so stopping there changes neither answer.

Search: for each state and position, only the earliest start that reaches it matters, because any later start that reaches the same state at the same position can continue in exactly the same ways. The live list is ordered by start (new starts are appended, and a step visits the list in order), so the first path to reach a state in a step carries the earliest start. The leftmost match start `s` is the earliest start of any match; every state on a path of a match from `s` carries start `s`, since an earlier start reaching it would give an earlier match. So the match state is seen with start `s` at the end of every match from `s`, and the last such position is the longest. Dropping later starts and new starts after the first match is safe, since they cannot be more leftmost.

### Complexity

- Time: O(m) to parse and build; O(n m) per match, count or search — the parser reads each character of the pattern once and the construction creates at most `m + 3` states; each character of the text visits each live state once and closes its target, and a closure visits each state at most once, so a step costs O(m).
- Space: O(m) — the tree, the automaton and every set of states hold at most O(m) entries, and the search keeps one start per live state; nothing grows with the text.

### Trade-offs

- A backtracking matcher is shorter to write and supports backreferences and lazy quantifiers, but its worst case is exponential; the cases include patterns such as `(a*)*b` and `(a|aa)*c` against long runs of `a`.
- Caching the sets of states as the states of a deterministic automaton (built lazily, one new state per new set) makes each character an array lookup, at the price of memory: in the worst case the deterministic automaton has exponentially many states, so a cache needs a bound and a way to fall back.
- The quadratic search, a fresh run from every start, is simpler and correct; it costs O(n^2 m) on a text with no match. The one-pass search costs O(n m) and the same space as a single run.
- Caching the automaton per pattern costs memory that a single call does not need; it pays off when one pattern is matched against many texts.

### Pitfalls and edge cases

- `ab|cd` is `(ab)|(cd)`, and `ab*` repeats `b` only. A parser that checks for `|` inside the sequence loop, or that wraps the sequence read so far when it sees `*`, gets the precedence wrong.
- Groups leave no node: `a(bc)d` is `cat('a',cat('b','c'),'d')`, not a flat `cat`, and `(a|b)|c` keeps its inner `alt`.
- Empty sequences are valid: the empty pattern, `()`, `a|` and `(|a)`. They need a state of their own in the automaton, or the fragment has no start.
- `*` right after `(` or `|` is `nothing-to-repeat`, not a repetition of an empty sequence; a `)` with no open group is an error, not the end of the pattern; the unclosed group reported is the innermost, at its own position.
- Breadth-first numbering, not depth-first and not creation order: `(ab|c)d` numbers `c` before `b`.
- The closure needs a seen set, both to count each state once and to terminate on loops of silent arrows such as `()*` and `(a*)*`.
- `fullMatch` must read the whole text: reaching the match state in the middle is not a match. The first set is part of `countSteps`, and the split states are counted like any other state.
- Search is leftmost first, then longest: `xyz|y` against `xyz` is `[0, 3]`, although `y` alone finishes first; `a*` against `baaa` is the empty match `[0, 0]`.
- In a class, a `-` before `]` is a literal; ranges include both ends; `^` negates only right after `[`; `]` outside a class is a literal.

### Language notes

- The tree is a tuple in Python, a tagged object in TypeScript, a small class or record in Java and Kotlin, a struct in Go and an enum in Rust. Rust's recursive enum needs `Box` (or a `Vec`) for its children.
- The automaton is three parallel arrays (kind, label, arrows) in every language, which keeps the renumbering a simple copy.
- Characters are compared by code: the text is printable ASCII, so Python's `str` comparison, TypeScript's UTF-16 code units, Java and Kotlin `char`, Go bytes and Rust `u8` all agree. Go and Rust index bytes, which is safe here for the same reason.
- `search` returns `int[]`: Kotlin builds an `IntArray` with `intArrayOf`, Java an `int[]`, Go a `[]int`, Rust a `Vec<i32>`.
- The parser recurses, which is safe because a pattern has at most 100 characters; the closure and the runs use explicit stacks and lists in every language.

## Further reading

- K. Thompson, "Regular expression search algorithm", Communications of the ACM 11(6), 419–422, 1968, [doi:10.1145/363347.363387](https://doi.org/10.1145/363347.363387): a compiler from a regular expression (juxtaposition, `|` and `*`, put in reverse Polish form first) to machine code, whose run examines each character of the text against a list of all the possible current states and builds the list of next states, instead of backtracking.
- J. A. Brzozowski, "Derivatives of regular expressions", Journal of the ACM 11(4), 481–494, 1964, [doi:10.1145/321239.321249](https://doi.org/10.1145/321239.321249): the theory that Thompson's paper relates its method to.
- The Open Group Base Specifications Issue 7 (IEEE Std 1003.1-2017), [chapter 9, Regular Expressions](https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/V1_chap09.html): section 9.1 defines the match as the one that begins earliest and, among those, the longest (9.1 states its rule that a null string is longer than no match for subexpressions); section 9.3.5 gives the bracket expression rules (`]` first and `-` first or last as literals, `^` first to negate) that level 4 follows, except that it rejects an empty class instead of reading `]` as its first item.
