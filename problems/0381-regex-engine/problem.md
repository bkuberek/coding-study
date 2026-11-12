# Regex Engine

## Statement

Build `RegexEngine`, a small regular expression engine: the part of a text editor's search box, a log filter or a form validator that decides whether a piece of text fits a pattern, and where. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**What is a regular expression?** A *regular expression* (a *regex*, or a *pattern*) is a short text that describes a set of strings. The pattern `ab*c` describes `ac`, `abc`, `abbc`, and so on: an `a`, any number of `b`, then a `c`. A *regex engine* answers questions such as "does the whole text `abbc` fit `ab*c`?" (yes) and "where is the first part of `xxabcx` that fits?" (from position 2 to position 5).

**How an engine works inside.** Most engines work like a small compiler, in three stages, and this problem builds them in that order:

1. *Parse* the pattern into a *syntax tree*, which makes its structure explicit: in `ab*|c`, the `*` applies to `b` only, and the `|` splits the whole pattern in two (level 1).
2. Turn the tree into an *automaton*: a set of states joined by arrows, some labeled with a character (level 2).
3. *Run* the automaton over the text, keeping track of every state it could be in, one character at a time (level 3). This never goes back to try another way, so the time grows in proportion to the text, whatever the pattern. Then use it to search inside a longer text, and add character classes such as `[a-z]` (level 4).

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 40, level 2 by 65, level 3 by 85 and level 4 by 115, keeping the last minutes for a final run.

## Input

- `RegexEngine()`: creates an engine. It keeps no state between calls, except any cache you choose to add.
- A **pattern** is a string of at most 100 printable ASCII characters (codes 32 to 126, space included). The patterns of levels 1 to 3 contain no `[` and no `]`.
- A **text** is a string of at most 2000 printable ASCII characters, possibly empty.
- Each level's section describes the methods it adds and their parameters.

## Output

Positions are indices of characters in the pattern or in the text, counted from 0. `parse` reports an invalid pattern with an error text. Every other method is called only with valid patterns: patterns for which `parse` returns no error.

## Level 1: Parse to a syntax tree

**The pattern language.** A pattern is built from these pieces:

| Piece | Matches |
|-------|---------|
| a *literal*: any character other than `.` `*` `+` `?` `\|` `(` `)` | exactly that character, so `a` matches `a` and a space matches a space |
| `.` | any one character |
| `X*` | `X` repeated zero or more times |
| `X+` | `X` repeated one or more times |
| `X?` | `X` zero times or once |
| `XY` | `X` followed by `Y` (*concatenation*) |
| `X\|Y` | either `X` or `Y` (*alternation*) |
| `(X)` | `X`, as one unit (a *group*) |

There is no escape character: the seven special characters cannot be matched as literals before level 4.

**Precedence.** As multiplication binds tighter than addition in arithmetic, the operators bind in this order, tightest first: repetition (`*`, `+`, `?`) applies to the single piece just before it; concatenation joins the repeated pieces into a sequence; alternation splits between sequences. So `ab*|c` means `(a(b*))|c`: a sequence `a`, `b*`, or the sequence `c`. Parentheses override this: `(ab)*` repeats the pair. Repetitions may be stacked: `a*?` is `(a*)?`.

**Empty parts.** A sequence may be empty, and then it matches the empty string: the empty pattern (no character at all), the group `()`, and each side of `|` in `a|` or `(|b)` can be empty.

As a grammar, with `*` here meaning "zero or more times":

```text
alternation := sequence ("|" sequence)*
sequence    := repetition*
repetition  := atom ("*" | "+" | "?")*
atom        := literal | "." | "(" alternation ")"
```

**The syntax tree.** `parse(pattern)` returns the tree as one line of text, built from these forms:

| Node | Written as |
|------|------------|
| a literal `c` | `'c'`: the character between single quotes, so a quote is `'''` and a space is `' '` |
| `.` | `any` |
| an empty sequence | `empty` |
| a sequence of two or more pieces | `cat(p1,p2,...)` |
| an alternation | `alt(s1,s2,...)`, one child per side of `\|`, left to right |
| `X*`, `X+`, `X?` | `star(X)`, `plus(X)`, `opt(X)` |

Children are separated by a comma, with no spaces. A sequence of exactly one piece is that piece, with no `cat` around it. A group leaves no node of its own: `(ab)` is `cat('a','b')`, and `a(bc)` is `cat('a',cat('b','c'))`, because a `cat` or `alt` holds the pieces of one sequence or the sides of one alternation, never the contents of a group inside it.

For example, `ab*|c` is `alt(cat('a',star('b')),'c')`: the alternation has two sides, the first a sequence of `a` and `b*`.

**Errors.** When the pattern is invalid, `parse` returns `"error: <code> at <position>"`:

| Code | When | Position |
|------|------|----------|
| `nothing-to-repeat` | a `*`, `+` or `?` has no piece before it: it is the first character of the pattern, or comes right after `(` or `\|` | that operator |
| `unmatched-paren` | a `)` closes no open `(` | that `)` |
| `unclosed-group` | the pattern ends while a `(` is still open | that `(`; when several are open, the one opened last |

The pattern is read from left to right, and the first problem found is the one reported. A group that is still open is found only when the pattern ends, so `)(` reports `unmatched-paren at 0`, and `(*` reports `nothing-to-repeat at 1`.

### Example 1

<!-- case: ex1 -->

`ab*|c` splits at the `|` into the sequences `ab*` and `c`, and the `*` applies to `b` alone. `(ab)+` repeats the whole group, and its tree has no node for the parentheses. In `a.?`, the `?` applies to `.`. `a(|b)` holds a group whose first side is empty, and the empty pattern is `empty`.

### Example 2

<!-- case: ex2 -->

In `a|*b` the `*` comes right after `|`, so it has nothing to repeat. In `(ab))` the second `)` at position 4 closes nothing. In `((a)` the `(` at position 0 is never closed. `a**` is valid: the repetitions stack.

## Level 2: Build the NFA

**Automata.** An *automaton* is a set of states joined by arrows. Reading a text, you start in a start state and follow arrows: an arrow out of a character state can be followed only by reading a character that the state accepts, and the arrows out of a *split* state can be followed without reading anything. The text matches when you can reach the match state just as the text ends. When a state has several arrows that can be followed, the machine may take any of them, so it is *nondeterministic*: an NFA. You will run it in level 3 by following all the choices at once.

**The construction.** Ken Thompson described in 1968 how to turn a regular expression into such a machine, one small piece per node of the tree. This problem uses the following form of his construction. There are five kinds of state:

| Kind | Arrows | Meaning |
|------|--------|---------|
| `char c` | one | accepts the character `c` |
| `any` | one | accepts any character |
| `split` | two or more, in order | follow any of the arrows without reading a character |
| `empty` | one | follow the arrow without reading a character |
| `match` | none | the pattern has matched |

Each node of the tree becomes a *fragment*: a start state and some *loose arrows*, arrows that do not point anywhere yet. Building the fragment of a parent fills in the loose arrows of its children:

| Node | Fragment |
|------|----------|
| `'c'`, `any`, `empty` | one new `char c`, `any` or `empty` state, which is the start; its arrow is loose |
| `cat(p1,...,pk)` | the fragments of `p1` to `pk`, the loose arrows of each pointed at the start of the next; the start of `p1` is the start; the loose arrows of `pk` stay loose |
| `alt(s1,...,sk)` | a new `split` state with `k` arrows, to the starts of `s1` to `sk` in that order; it is the start; the loose arrows of all the sides stay loose |
| `star(X)` | a new `split` with two arrows: the first to the start of `X`, the second loose. The loose arrows of `X` point back at the `split`, which is the start |
| `plus(X)` | the same `split` and arrows as `star(X)`, but the start of `X` is the start: `X` runs once before the loop |
| `opt(X)` | a new `split` with two arrows: the first to the start of `X`, the second loose. The `split` is the start; the loose arrows of `X` stay loose, next to the second arrow |

Finally, one `match` state is added and every loose arrow of the whole pattern is pointed at it.

**Numbering.** The states are numbered by a *breadth-first walk* from the start state: the start state is `0`; then the states are visited in number order, and each one's arrows are read in order; a target not numbered yet gets the next number. Every state can be reached from the start, so every state gets a number, and the numbering does not depend on the order in which you created the states. An automaton has at most 3 more states than its pattern has characters (a pattern made only of `|` reaches that), so at most 103.

- `nfa(pattern)`: the states, one line each, in number order. A line is `"<n>: <kind>"`, followed by `" -> "` and the arrows' target numbers in order, separated by `", "`, when the state has arrows. A character state is written `char 'c'`, with the character between single quotes as in level 1. For example `"0: split -> 1, 2"`, `"1: char 'a' -> 3"`, `"3: match"`.

### Example 1

<!-- case: ex3 -->

For `a|b`, the `split` at 0 leads to one character state per side, and both point at the match state. For `ab*`, state 1 is the `split` of the `star`: its first arrow enters the loop, whose `char 'b'` points back at it, and its second arrow leaves to the match state.

### Example 2

<!-- case: ex4 -->

For `(a|b)*c`, the outer `split` (state 0) is the start of the `star`; its first arrow goes to the inner `split` of the alternation, and its second to `char 'c'`. The breadth-first walk numbers the states one arrow distance at a time, so `c` is 2 although it comes last in the pattern. For `x+y?`, `x` comes first, then the loop's `split` at 1, then the `split` of `y?`, whose second arrow and `y` both lead to the match state.

## Level 3: Simulate without backtracking

**Running the machine.** Because an NFA may have several choices, the simplest way to run it is to try one path, and when it fails, go back and try the next: *backtracking*. Thompson's idea was to follow all the paths at once. Keep the **set** of states the machine could be in:

1. The *closure* of a set of states is the set itself plus every state reachable from it by following `split` and `empty` arrows, as many as you like, without reading a character.
2. The first set is the closure of `{0}`.
3. For each character of the text, in order: the next set is the closure of the targets of the arrows of the states in the current set that accept that character. When the next set is empty, stop: nothing can match anymore.
4. The whole text matches when every character was read and the last set holds the match state.

A state appears in a set at most once, however many paths lead to it. A set never holds more states than the automaton has, so the work is at most the number of states for each character. Walk the closure with a stack or a queue of your own and a set of the states already reached: an `empty` or `split` state can lead back to itself, as in `()*` and `(a*)*`.

**Counting steps.** One *step* is one state entering one set. `countSteps` is the sum of the sizes of all the sets built: the first set, then the set after each character read, until the text ends or a set is empty (an empty set adds 0).

**Why this matters.** Take `(a|aa)*c` and a text of 30 letters `a` and no `c`. The 30 letters can be cut into pieces `a` and `aa` in 1,346,269 ways, and a matcher that backtracks tries every one of them, fails at the end because no `c` follows, and goes back to try the next. Each extra letter multiplies the number of ways by about 1.6, so 60 letters give about 2.5 * 10^12. The set never holds more than the 7 states of this automaton, and here it holds 6 after each letter, so 30 letters cost 185 steps and each extra letter adds 6. The time of the simulation grows with the length of the text times the size of the pattern, never exponentially.

- `fullMatch(pattern, text)`: `true` when the whole text matches the pattern, from its first character to its last.
- `countSteps(pattern, text)`: the number of steps of the run that decides `fullMatch`, at most `(2000 + 1) * 103`.

### Example 1

<!-- case: ex5 -->

The automaton of `(a|b)*abb` is the one of level 2 with `abb` in place of `c`. The first set is the closure of state 0: the two `split` states and the three character states they lead to, 5 states. After each letter the set has 6 states, so `aabb` costs 5 + 4 * 6 = 29 steps and ends in the match state. `abab` also costs 29 steps but ends elsewhere. For `abbc` the set after `c` is empty, so the run stops there: 5 + 3 * 6 + 0 = 23.

### Example 2

<!-- case: ex6 -->

The pattern from "Why this matters". `aaaac` matches. With 30 letters `a` the answer is `false` after 185 steps, and one more letter adds 6 steps, where a backtracking matcher would need about 1.6 times as many tries.

## Level 4: Search and character classes

**Character classes.** From this level on, patterns may contain *classes*. A class is an atom: it matches one character from a list, and it can be repeated like any atom.

- `[` starts a class and `]` ends it. Inside, the characters are *items*: `[abc]` matches `a`, `b` or `c`.
- `x-y` inside a class is a *range*: it matches every character whose code is from the code of `x` to the code of `y`, both included. `[a-z0-9_]` matches a small letter, a digit or `_`. A `-` is a range only between two characters: first in the list (after `^`, if any) or right before `]`, it is the literal `-`.
- `^` right after `[` makes the class *negated*: `[^0-9]` matches any character that is not a digit. Elsewhere in a class, `^` is a literal.
- Inside a class every other character is a literal, the special characters of level 1 and `[` included: `[.*]` matches a dot or a star.
- Outside a class, `]` is a literal.

`parse` writes a class as `class(i1,i2,...)` or, negated, `notclass(i1,i2,...)`, with the items in the order written, each a quoted character `'c'` or a quoted range `'x'-'y'`, separated by commas. In the automaton, a class is one state with one arrow, written as in the tree: `"2: class('a'-'z','_') -> 3"`. It accepts a character as the class matches it.

Three new errors, reported by `parse` as in level 1:

| Code | When | Position |
|------|------|----------|
| `unclosed-class` | the pattern ends inside a class | its `[` |
| `empty-class` | the class has no item: `[]` or `[^]` (so, unlike some engines, `]` cannot be the first item) | its `[` |
| `bad-range` | a range whose second character has a smaller code than its first, such as `z-a` | the first character of the range |

A class is read from left to right like the rest of the pattern. When the pattern ends inside a class that is itself inside an open group, the class is the innermost open construct, so the error is `unclosed-class`.

**Search.** Most of the time a pattern is looked for *inside* a text. Several parts of the text may match; this engine reports the one that the POSIX standard for regular expressions chooses, the **leftmost-longest** match: the match that begins earliest in the text and, among the matches that begin there, the longest. An empty match counts, and it is better than no match at all: `a*` matches the empty string at position 0 of `baaa`, before the `aaa` that starts at 1.

- `search(pattern, text)`: `[start, end]`, the positions where the leftmost-longest match begins and where it ends, `end` excluded, so the match is `text[start:end]`; `[-1, -1]` when no part of the text matches.

### Example 1

<!-- case: ex7 -->

A class with three items, one of them `_`, then a negated class that matches anything but a space. In `[-a.]` the `-` is first, so it is a literal, and `.` is a literal inside a class. `[]` has no item. In `[b-a]` the range ends before it starts, and the error points at `b`. The automaton of `[^a-c]x` has one state for the class.

### Example 2

<!-- case: ex8 -->

`[a-z]+` does not match `H`, so the first match is the `i` at position 1, and it cannot be longer because a space follows. `a*` matches the empty string at 0, which begins earlier than `aaa`. Both `cat` and `category` begin at 4 in `the category`; the longer one wins. No digit gives `[-1, -1]`.

## Constraints

- At most 200 calls per test.
- A pattern has at most 100 characters, so whatever you build from it is at most about 100 levels deep: recursion over the pattern or its tree is safe in every language.
- A text has at most 2000 characters. Walk the text with a loop, not by recursion.

## Follow-ups

- The sets of states repeat: after a few characters, most texts only move between a handful of sets. How would you cache "this set, then this character, gives that set", building a deterministic automaton lazily, and what bounds its memory?
- `search` with a fresh run from every start position takes time proportional to the square of the text. How can one pass over the text find the leftmost-longest match, by remembering for each state the earliest start that reaches it?
- Add capture groups: report where each parenthesized group matched. Why does that need more than a set of states, and what extra information would each state carry?
- Backtracking engines support *backreferences* (`(a+)b\1`), which this engine cannot. Why can no finite automaton match "the same text again"?

## Hints

### Hint 1

Start with the grammar: write one function per line of it. All of them share the pattern and one position in it, which each function moves forward past the characters it reads. `alternation` calls `sequence` and loops while it sees `|`; `sequence` calls `repetition` until it sees `|`, `)` or the end; `repetition` reads one atom and then wraps it once per `*`, `+` or `?` that follows; `atom` reads one character, or after `(` calls `alternation` again and then expects `)`. Each function returns a node of the tree. This way of parsing, one function per rule, is called *recursive descent*.

### Hint 2

The precedence comes for free from which function calls which: because `repetition` wraps only the atom it just read, `ab*` repeats `b` alone, and because `alternation` sits on top, `|` splits whole sequences. Check every error at the moment you meet it: a repetition operator where an atom should start, a `)` left over when the top-level `alternation` returns, the end of the pattern where a group expects `)`.

### Hint 3

Build the automaton with a function that takes a node and returns its start state and the list of its loose arrows, recorded as (state, arrow index) pairs. A parent creates its own `split` state, if it needs one, and fills in the loose arrows of its children. Number the states only at the end, with a queue from the start state, and rewrite every arrow with the new numbers.

### Hint 4

For the simulation, write `closure(states)` with a stack and a set of the states already reached: pop a state; if it was reached before, skip it; otherwise add it, and when it is a `split` or an `empty` state, push its targets. Each character then costs one pass over the current set and one closure. Count the steps by adding the size of each set as you build it.

### Hint 5

Several states of the set can lead to the same state, and an `empty` loop such as `()*` can lead back to the state you started from. Both are why the closure keeps a set of reached states: a list without it counts a state twice, or never ends.

### Hint 6

For a class, store the items as (low, high) pairs, a single character being a pair with equal ends, and the negation flag; a character matches when it lies in some pair, and the flag inverts that. Read a range only when a `-` follows the first character and the character after the `-` is not `]`.

### Hint 7

Search is many runs of level 3 in one: a run that starts at some position can match at several ends. Which start positions do you need to try, in which order, and when may a run stop? Leftmost comes before longest.

### Hint 8

For one pass instead: give each state of the set the earliest start position that reaches it, add the start state's closure at every position until a match has been seen, and when two paths reach a state keep the earlier start. Once a match has been seen, drop every state whose start is later than the match's start, and keep going while states remain, since a longer match, or an earlier start that is still in progress, may come.
