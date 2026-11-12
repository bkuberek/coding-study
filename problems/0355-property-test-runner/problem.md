# Property Test Runner

## Statement

Build `PropertyRunner`, a small engine for **property-based testing**. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**Examples versus properties.** An *example-based* test checks one input that the author picked: "sorting `[3, 1, 2]` gives `[1, 2, 3]`". It is easy to read, but it only tests the inputs the author thought of, and bugs tend to live in the inputs nobody thought of: the empty list, negative numbers, repeated values. A *property-based* test states a rule that must hold for *every* input, such as "the output of a sort is in non-decreasing order", and a tool checks the rule on many inputs that it makes up. The recipe has three parts:

1. A **generator** makes inputs, for example "lists of 0 to 6 integers between 0 and 9".
2. A **property** is a rule that every input must satisfy, a check that answers yes or no.
3. A **runner** draws many inputs, checks the property on each, and reports the first one that breaks it, called a **counterexample**.

**A worked example.** Suppose someone wrote a sort that makes only one pass over the list, swapping each pair of neighbours that are out of order. The example test passes: one pass over `[3, 1, 2]` swaps `3` with `1` and then `3` with `2`, which gives `[1, 2, 3]`. The property "the output is in non-decreasing order", checked on 100 random lists, fails on the second list drawn in this problem's level 1 examples, `[5, 3, 4, 2, 0, 9]`: one pass gives `[3, 4, 2, 0, 5, 9]`. The property found the bug that the example missed.

**Why everything is fixed here.** Real tools draw their inputs at random. To make every answer exact and the same in every language, this problem draws them from a small pseudo-random generator that is specified bit by bit, started from a **seed**: the same seed gives the same inputs. Generators and properties travel through the tests as short strings in a small language described below, because a test case can hold only data.

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 40, level 2 by 70, level 3 by 95 and level 4 by 115, keeping the last minutes for a final run.

## Input

- `PropertyRunner()`: creates a runner.
- A **seed** is an integer from `1` to `2^31 - 1`.
- A **count** or a number of **runs** is an integer from `0` to `1000`.
- Generators and properties are strings of words separated by single spaces. Integers in them are written in decimal, with `-` for negative numbers. The tests only pair a property with a generator whose values have the shape the property reads.
- Each level's section describes the methods it adds and their parameters.

## Output

Values are reported as text: an integer in decimal, such as `-7`; a list as its elements inside brackets, separated by commas without spaces, such as `[5,3,4]` or `[]`. Level 3 adds pairs.

## Level 1: Generators and runs

**The random numbers.** All randomness comes from one **xorshift32** generator. Its state is a 32-bit unsigned integer, set to the seed at the start. Each draw updates the state with three steps and returns the new state:

```text
x = x XOR (x << 13), keeping the low 32 bits
x = x XOR (x >> 17)
x = x XOR (x << 5), keeping the low 32 bits
```

Here `<<` and `>>` are bit shifts and `>>` fills with zeros. From seed `1` the first draw is `1 XOR 8192 = 8193`, then `8193 XOR 0 = 8193`, then `8193 XOR 262176 = 270369`. The numbers are unsigned: they go up to `2^32 - 1`, so a language whose 32-bit integers are signed needs a wider type or unsigned operations.

**An integer between `low` and `high`**, inclusive, is `low + (r mod (high - low + 1))` for the next draw `r`.

**Generators.** A generator is written in prefix form: the name of the generator comes first, then its numbers, then the generators it is built from.

- `int LOW HIGH` (with `-10^6 <= LOW <= HIGH <= 10^6`): an integer between `LOW` and `HIGH`, from one draw.
- `list MIN MAX G` (with `0 <= MIN <= MAX <= 20`): first the length, an integer between `MIN` and `MAX` from one draw, then that many elements from the generator `G`, one after another. At this level `G` is an `int` generator: `list 0 5 int 0 9` is a list of 0 to 5 digits.

**Properties.** A property is one of these names, some followed by an integer `K`:

| Property | Reads | Holds when |
|----------|-------|------------|
| `lt K` | an integer `x` | `x < K` |
| `not-multiple K` | an integer `x` (`K >= 1`) | `x` is not a multiple of `K`; `0` is a multiple of every `K` |
| `sum-lt K` | any value | the sum of all the integers in it is less than `K`; the sum of `[]` is `0` |
| `len-lt K` | a list | its length is less than `K` |
| `ordered` | a list | each element is less than or equal to the next |
| `sort-ordered` | a list | the list sorted in increasing order is `ordered`. It always holds: the sort is correct |
| `one-pass-ordered` | a list | the list after one pass of the buggy sort is `ordered`. The pass goes from the first position to the last but one and swaps an element with the next one when it is greater |
| `max-from-zero` | a list | the list is empty, or a buggy maximum, which starts at `0` and takes the larger of it and each element, equals the real maximum |

`sort-ordered`, `one-pass-ordered` and `max-from-zero` stand for functions under test, one correct and two with a bug.

- `randoms(seed, count)`: the first `count` numbers the generator returns from `seed`.
- `generate(gen, seed, count)`: the first `count` values that the generator `gen` makes, drawn one after another from one stream started at `seed`, as text.
- `check(gen, prop, seed, runs)`: draws `runs` values one after another, from one stream started at `seed` (the same values `generate` lists), and checks the property `prop` on each, in order. At the first value for which the property does not hold, it stops and returns `failed <k>: <value>`, where `k` is the number of that run, counted from `1`. When the property holds for all the values, it returns `passed <runs>`.

### Example 1

<!-- case: ex1 -->

The first draws from seed `1` are `270369`, `67634689` and `2647435461`, and their remainders by 10 are `9`, `9` and `1`, the first digits `int 0 9` makes. `int -10 10` takes the remainder by 21 and adds `-10`. With seed `7`, the seventh value of `int 0 100` is `100`, the first that is not below 50. Every value is below 101, so that property passes all 100 runs.

### Example 2

<!-- case: ex2 -->

A list draws its length, then its elements: `[5,7,5]` took four draws. The correct sort passes 100 lists. The one-pass sort fails on the second list, the one from the worked example, and the buggy maximum fails on the first list whose elements are all negative, `[-7]`, where it answers `0`.

## Level 2: Shrinking

A random counterexample is often large and noisy: `[5,3,4,2,0,9]` hides the bug in six numbers. **Shrinking** turns it into a small one that still fails, such as `[1,1,0]`, which shows the bug at a glance: a single pass moves the `0` back only one step. A shrinker needs, for every value, a list of **candidates**: values that are simpler and that the generator could have made. Starting from the counterexample, it tries the candidates in order and moves to the first one that still fails, then does the same from there, until no candidate fails. This is a greedy search: it finds a value that cannot be made simpler one step at a time, which is small but not always the smallest that fails.

**Candidates of an integer** made by `int LOW HIGH`. The **target** is the integer between `LOW` and `HIGH` closest to zero: `0` when the range holds `0`, `LOW` when `LOW > 0`, `HIGH` when `HIGH < 0`. An integer `x` equal to the target has no candidates. Otherwise, let `d = x - target`. The candidates are the target, then `x - d/2`, `x - d/4`, `x - d/8` and so on, each division **rounded toward zero**, stopping before the first quotient that is `0`. For `x = 100` with target `0` they are `0, 50, 75, 88, 94, 97, 99`, and for `x = -7` they are `0, -4, -6`. They come closer to `x` step by step, so a shrinker tries big jumps first.

**Candidates of a list** made by `list MIN MAX G`, of length `n`:

1. **Shorter lists.** For a chunk size `c` equal to `n`, then `n/2`, `n/4` and so on, rounded down, while `c >= 1`: for each start `i = 0, c, 2c, ...` with `i + c <= n`, the list without the `c` elements from position `i`. A chunk size is skipped when `n - c < MIN`. The first candidate of a list that may be empty is `[]`.
2. **Simpler elements.** For each position from the first to the last, and for each candidate of the element there (by `G`'s rules, in order), the list with that one element replaced.

A candidate that equals the value itself, or an earlier candidate, is left out: removing either of two equal neighbours gives the same list once.

- `candidates(gen, seed, index)`: the candidates, as text and in order, of the `index`-th value (counted from `1`) that `gen` makes from `seed`, the last value `generate(gen, seed, index)` would list.
- `minimize(gen, prop, seed, runs)`: `[]` when `check` with the same arguments would not report a failure. Otherwise the **shrink path**: the counterexample `check` reports, then every value the shrinker moved to, in order. The last entry is the shrunk counterexample.

### Example 1

<!-- case: ex3 -->

The candidates of `100` halve the distance to `0` each time. `lt 50` fails on `100`; the first candidate that also fails is `50`, and none of the candidates of `50` fails, so `50` is the smallest value that breaks the property. The candidates of `-7` round their halves toward zero. `not-multiple 7` fails on `21` and shrinks to `0`: zero is a multiple of 7 too, which the property did not mean to allow.

### Example 2

<!-- case: ex4 -->

`[5,7,5]` first offers `[]`, then itself without one element, then each element shrunk in turn. The one-pass sort's counterexample loses elements, then values, step by step, down to `[1,1,0]`. A property that never fails has nothing to shrink.

## Level 3: Composed generators

Real inputs have structure: a pair of an id and a list, a list of key-value pairs, an integer that must be even. Composed generators build them from smaller generators, and their shrinking follows the same structure, so that every candidate is still a value the generator could make.

- `pair A B`: a pair, the first part from `A`, then the second from `B`. Its text is `(<first>,<second>)`, such as `(7,[2,1])`.
- `filter NAME G`: a value from `G` that passes the filter `NAME`. It draws from `G` until a value passes. Every value that fails the filter is **discarded**. Filters:

| Filter | Reads | Lets through |
|--------|-------|--------------|
| `even`, `odd` | an integer | even integers, odd integers |
| `nonzero`, `positive` | an integer | integers other than `0`, integers above `0` |
| `nonempty` | a list | lists with at least one element |
| `distinct` | a list | lists where no two elements have the same text |
| `unequal` | a pair | pairs whose two parts have different texts |

- Generators now nest in any way: `list 0 6 pair int 0 5 int 0 9` is a list of up to 6 pairs, and a `list` takes any generator for its elements.
- Two more properties read lists of pairs: `keys-distinct` holds when the first parts of the pairs all have different texts, and `map-keeps-last` stands for a map with a bug that ignores a write to a key it already has. It holds when, for every first part, the second part of its first pair has the same text as the second part of its last pair. `sum-lt K` adds every integer in any value, pairs included.

**Shrinking composed values.**

- The candidates of a pair are its first part's candidates, each with the same second part, then its second part's candidates, each with the same first part.
- The candidates of a filtered value are the candidates of its inner generator that pass the filter, in the same order. Shrinking must never produce a value the generator could not make.
- A list shrinks its elements with their own generator's rules, whatever that generator is. Every list of candidates leaves out repeats and the value itself, as at level 2.

**Discards.** A filter that rarely lets a value through can make a run draw forever. Each call to `generate`, `check`, `candidates` or `minimize` counts its discards, in every filter, nested or not. When the count goes above the **discard limit**, the call **gives up** at once: `generate` returns the values completed before, `check` returns `gave up after <k>` with `k` the number of runs that passed, and `minimize` and `candidates` return `[]`. Shrinking draws nothing, so it discards nothing.

- `setDiscardLimit(limit)`: sets the discard limit (from `0` to `10^4`) for the calls that follow. It starts at `100`.

A filter is convenient but costly: it can throw away much of what it draws, and it tilts the inputs toward the values that pass easily, such as short lists for `distinct`. A generator that builds valid values directly is usually better.

### Example 1

<!-- case: ex5 -->

A pair draws its first part, then its second. The even filter discards the odd values it draws. When `38` is shrunk for `lt 11`, only even candidates are tried. The candidates of `14` are `0`, `7`, `11` and `13`, and only `0` is even, which passes, so the shrinker stops at `14`, although `12` would fail too: no single step reaches it. Without the filter, the same property shrinks to `11`.

### Example 2

<!-- case: ex6 -->

The list of pairs repeats the key `3`. `keys-distinct` keeps the two pairs with that key and shrinks their second parts to `0`, giving `[(3,0),(3,0)]`. `map-keeps-last` needs the two values to differ, so it stops at `[(3,0),(3,1)]`: the map keeps `0` where the last write said `1`. With a limit of 5 discards, lists of 5 to 8 distinct digits from `0` to `3` cannot be drawn, and the check gives up before any run passes.

## Level 4: Stateful testing

Some code is not a function from input to output but an object whose answers depend on what happened before: a queue, a cache, a bank account. A property of one call says little about it. **Model-based testing** checks it with a *sequence of commands*: the runner sends the same commands to the **system under test** and to a **model**, a simple and obviously correct version, and compares their answers after every command. A sequence where an answer differs is a counterexample, and it is shrunk like a list.

**The queue.** The model is a first-in, first-out queue that holds at most `capacity` values (1 to 5). Its commands:

- `put V` (with `V` from `0` to `9`): when the queue holds fewer than `capacity` values, adds `V` at the back and answers `ok`; otherwise answers `full`.
- `get`: removes the value at the front and answers it, such as `7`. The queue's contract forbids `get` on an empty queue: a caller must look first. In testing terms this is a **precondition**: a sequence where a `get` comes while the *model* is empty is not a valid test.
- `size`: answers how many values the queue holds, such as `2`.

**The system under test** is the same queue with one planted **bug**, chosen by name:

| Bug | What goes wrong |
|-----|-----------------|
| `none` | nothing: it behaves as the model |
| `size-wraps` | `size` answers the count modulo `capacity`, so a full queue says `0` |
| `full-overwrites` | `put` on a full queue removes the front value, adds `V` at the back and answers `ok` |
| `repeat-dropped` | `put V` on a queue that is not full and whose back value equals `V` answers `ok` without adding anything |
| `wrap-lifo` | once more than `capacity` puts have answered `ok` since the start, `get` removes and answers the value at the *back* |

When the system under test's own queue is empty at a `get` (a bug can lose values), it answers `empty`.

**Random sequences.** One sequence is drawn as follows: its length is an integer between `1` and `maxLength`, from one draw. Then, for each command, with a fresh model that the drawn commands are applied to as they are drawn: the allowed commands, in the order `put`, `get`, `size`, are all three when the model holds a value and `put` and `size` when it is empty; the command is the allowed one at position `r mod (number allowed)` for the next draw `r`; a `put` then draws its value, an integer between `0` and `9`. Sequences are written as their commands joined by `, `, such as `put 3, get, size`.

**Running and shrinking.** A run sends the sequence to a new model and a new system under test; it fails when some command gets different answers. The candidates of a sequence of `n` commands are those of a list: first the shorter sequences, by chunk sizes `n`, `n/2`, `n/4` and so on, never shorter than one command; then, for each `put` from the first to the last, its value replaced by each candidate of an `int 0 9` value. A candidate that repeats an earlier one or the sequence itself is left out, and so is a candidate that breaks the precondition: removing a `put` can leave a later `get` with nothing to take. The shrinker moves to the first candidate that fails, as at level 2.

- `replay(capacity, bug, commands)`: sends `commands` to a new system under test and returns its answers, one per command. A command that breaks the precondition, judged by a model that receives the same commands, gets the answer `invalid`, and nothing after it is sent.
- `generateCommands(capacity, seed, count, maxLength)`: the first `count` sequences drawn one after another from one stream started at `seed`, each as text.
- `firstFailure(capacity, bug, seed, runs, maxLength)`: draws up to `runs` sequences one after another from one stream started at `seed`, and returns the first that fails, as a list of commands. `[]` when none fails.
- `shrinkFailure(capacity, bug, seed, runs, maxLength)`: the sequence `firstFailure` returns, shrunk; `[]` when none fails.

This is why stateful tests pay off: a bug that needs "fill the queue, empty it, fill it again" is hard to think of as an example, but random sequences hit it, and shrinking turns a ten-command mess into the three or five commands that matter.

### Example 1

<!-- case: ex7 -->

The model accepts two values, refuses the third, and gives them back in order. The buggy queue answers the same, except that `size` says `0` when the queue is full. In the last sequence the second `get` comes when the model is empty, so it is `invalid` and the replay stops there.

### Example 2

<!-- case: ex8 -->

The first sequence from seed `1` has four `size` commands, since a `get` is never drawn while the model is empty. The first sequence that catches `size-wraps` has ten commands. Shrinking removes all but two puts and a `size`, then shrinks both values to `0`: fill the queue, then ask its size.

## Constraints

- At most 60 operations per test.
- `runs` and `count` are at most 1000, and `index` from `1` to 1000; a level 4 sequence has at most 20 commands.
- A generator string has at most 20 words, and nests at most 4 deep.

## Follow-ups

- Real tools can start with small inputs and let a size bound grow over the runs, so that early runs try tiny values. How would you add a size parameter that bounds list lengths and integer ranges, and how would shrinking change?
- Greedy shrinking stops at local minima where two values must change together, such as two equal values that a bug needs. How could a shrinker try changing two elements at once, and what does it cost?
- Some tools shrink the stream of random draws instead of the value, and then run the generator again. Why does that make every candidate a valid value without any filter-specific rules?
- A stateful run here compares answers command by command. How would you test a queue that several threads use at once, where more than one answer can be right?

## Hints

### Hint 1

Write the random generator first and check it against `randoms`: from seed `1` the first number is `270369`. In a language with signed 32-bit integers, mask to 32 bits after each left shift and use an unsigned right shift, or keep the state in a 64-bit integer and mask.

### Hint 2

Split the generator string on spaces and read it with a function that takes the list of words and a position, and returns a parsed generator and the position after it. `list` and `pair` call the same function for their inner generators, so nesting comes for free.

### Hint 3

Represent a generated value as a small tree: an integer, a list of values, or a pair of values. Write one function that turns it into text, one that sums its integers, and one that draws it from a parsed generator and the random stream. Then `generate` and `check` are short loops.

### Hint 4

Write the candidates of an integer and of a list as two functions that take the parsed generator and the value. For a list, make the removals first, then call the element generator's candidate function for each position. Use the text of each candidate to drop repeats.

### Hint 5

The shrinker is a loop: compute the candidates of the current value, find the first one for which the property fails, make it the current value, and stop when there is none. Each step makes the value strictly simpler, so the loop ends.

### Hint 6

A filter's candidates are its inner generator's candidates that pass it. For discards, keep a counter in the object that carries the random stream, and raise an error or return a flag when it goes above the limit, so that every caller can stop.

### Hint 7

For level 4, write the queue once, with a `bug` field that is `none` for the model. A run creates two of them and compares answers. Generation needs its own model, to know when `get` is allowed. Shrinking reuses the list removals, adds the `put` value shrinks, and keeps only candidates that replay without an `invalid`.
