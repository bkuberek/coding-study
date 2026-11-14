# Logical Clocks

## Statement

Build `LogicalClocks`, which puts timestamps on the events of a small distributed system: a few *processes* (machines, or programs on them) that each do their own work and talk only by sending *messages*. You get the history as a script, one event at a time, and the class answers questions about the order of the events. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working.

**Why there is no shared clock.** Each machine has its own clock, and no two clocks agree exactly: they run at slightly different speeds, and when they are synchronized over the network, the messages that carry the time take an unknown time to arrive. So one machine may read `100` at the moment another reads `95`. Sorting events by these readings can put an effect before its cause: a message can seem to arrive before it was sent. This problem keeps the readings, because level 4 needs them, but levels 1 to 3 order events without them.

**What "happened before" means.** Leslie Lamport's 1978 paper defines it from what could have influenced what, not from time. Event `a` *happened before* event `b`, written `a → b`, when:

1. `a` and `b` are on the same process and `a` comes first;
2. `a` sends a message and `b` receives that same message; or
3. there is an event `x` with `a → x` and `x → b` (so influence travels along chains of messages).

Two events are *concurrent* when neither happened before the other. Concurrent does not mean "at the same instant": it means that neither could have influenced the other.

A worked example with two processes, time running to the right:

```text
process 0:   a1 ------ a2 (send) ------------------------- a3 (receive)
                         \                                /
process 1:   b1 ---------- b2 (receive) ---- b3 (send) --
```

Here `a1 → a2` (same process), `a2 → b2` (the message), and so `a1 → b2` and `a1 → a3` (chains). But `a1` and `b1` are concurrent: no message connects them, whatever the clocks said when they happened.

Aim to finish in 90 minutes. A good split: read the statement in the first 10 minutes, finish level 1 by about minute 30, level 2 by 50, level 3 by 70 and level 4 by 85, keeping the last minutes for a final run.

## Input

- `LogicalClocks(processes)`: a system of `processes` processes, numbered `0` to `processes - 1`, with no events yet.
- `process`: the number of the process an event happens on.
- `event`: the name of a new event, unique in the whole history: 1 to 20 printable ASCII characters (codes 33 to 126).
- `wall`: what the process's own physical clock reads when the event happens, in milliseconds. Readings of different processes are not synchronized, and the readings of one process may even go backwards, as when its clock is set back.
- Each level's section describes the methods it adds and their parameters.

## Output

The methods that record an event (`local`, `send`, `receive` and level 3's `write`) return the event's Lamport timestamp (level 1), or `-1` when the call is refused: then **nothing is recorded**, no clock moves and a message that was not received stays unreceived. A call is refused when `process` is outside `0` to `processes - 1` or when the name `event` is already used, and in the cases each level lists.

A question about a name that is not a recorded event gets the empty answer: `""` for a text and `[]` for a list. Texts are compared by the numeric codes of their characters, so `B` comes before `a` and `10` before `9`; process numbers are compared as numbers.

## Level 1: Lamport clocks

- `local(process, event, wall)`: an event inside one process that no other process sees, such as a step of a computation.
- `send(process, event, wall)`: the process sends a message. A message is named after the event that sends it, so `send(0, "m1", ...)` sends the message `"m1"`.
- `receive(process, event, message, wall)`: the process receives the message `message`. It is refused when `message` is not the name of a send event, when that message was received already (each message is received once), and when `process` is the process that sent it.
- `totalOrder()`: the names of all recorded events, ordered by Lamport timestamp, and events with equal timestamps by process number, smallest first.

**Lamport's clock.** Every process keeps a counter `C`, which starts at `0`.

1. A local event or a send adds one: `C = C + 1`. The event's timestamp is the new `C`, and a send puts it into its message.
2. A receive of a message stamped `T` jumps past both: `C = max(C, T) + 1`. The event's timestamp is the new `C`.

The paper states these rules as conditions (a process advances its counter between any two of its events; on a receive it sets the counter to at least its present value and to more than `T`), and any increase that meets them works. This problem fixes the smallest one, so every answer is exact.

The rules give the paper's *clock condition*: if `a → b`, then the timestamp of `a` is smaller than the timestamp of `b`. The converse does not hold: a smaller timestamp does not mean that the event happened before, since concurrent events get timestamps in any order. Level 2 fixes that.

**A total order.** Sorting by timestamp and breaking ties by process number puts every event in one sequence that all processes can compute alike, without asking anyone: the paper uses it to grant a shared resource to requests in the order in which they were made. Because of the clock condition, the order never puts an event before something that happened before it.

### Example 1

<!-- case: ex1 -->

The wall clock of process 1 runs behind: it receives `a2` at `95`, while process 0 sent it at `102`. Sorting by those readings would put the receive `b2` before the send `a2`. The counters do not care: `a1` and `a2` get `1` and `2`, `b1` gets `1`, and the receive `b2` jumps past the message's `2` to `3`. `b3` sends `4`, so `a3` jumps from `2` to `5`. In the total order `a1` and `b1` share the timestamp `1` and process 0 comes first.

### Example 2

<!-- case: ex2 -->

`x`, `y` and `z` all get the timestamp `1`; the total order lists them by process number (`y` on 0, `z` on 1, `x` on 2), not by name or by call order. `w` receives `x`. The next four calls are refused: `y` is not a send, process 3 does not exist, the name `z` is taken, and `x` has been received already. A refused call records nothing, so the total order has four events.

## Level 2: Vector clocks

A Lamport timestamp is one number, and it cannot tell "before" from "concurrent". A *vector clock* keeps one counter per process instead: entry `j` of a process's vector is how many events of process `j` it knows of, its own included. Knowledge travels in the messages. Colin Fidge (1988) and Friedemann Mattern (1989) described it independently.

**The rules.** Every process `p` keeps a vector `V` of `processes` counters, all `0` at the start.

1. A local event or a send adds one to its own entry: `V[p] = V[p] + 1`. The event's vector is a copy of the new `V`, and a send puts it into its message.
2. A receive of a message with vector `M` first takes, entry by entry, the larger of the two: `V[j] = max(V[j], M[j])` for every `j`. Then it adds one to its own entry, `V[p] = V[p] + 1`, and the event's vector is a copy of `V`.

**Comparing.** Write `A ≤ B` when `A[j] ≤ B[j]` for every `j`. Then `a → b` exactly when the vector of `a` is `≤` the vector of `b` and the two differ. When neither vector is `≤` the other, the events are concurrent. (Two different events never have the same vector.)

- `vector(event)`: the event's vector, entry `j` for process `j`.
- `compare(first, second)`: `"before"` when `first → second`, `"after"` when `second → first`, `"concurrent"` when neither, `"same"` when both names are the same event, and `""` when either name is not a recorded event.

### Example 1

<!-- case: ex3 -->

`b2` receives `a2`, which carries `[2, 0, 0]`, while process 1 has `[0, 1, 0]` from `b1`. The larger entries give `[2, 1, 0]`, and its own entry goes up: `[2, 2, 0]`. `a1` (`[1, 0, 0]`) is `≤` it, so `a1` is before `b2`. `c2` (`[0, 0, 2]`) and `b2` are concurrent, although the Lamport timestamp of `c2`, `2`, is smaller than that of `b2`, `3`. `b1` and `a2` are concurrent too. An event compared with itself is `"same"`, and an unknown name gives `""` and `[]`.

### Example 2

<!-- case: ex4 -->

Knowledge travels along a chain: `x1` reaches process 1 in a message, process 1 sends on, and `z1` on process 2 receives it. So `x1` is before `z1`, which carries `[1, 2, 1]`, although process 0 never sent anything to process 2. `x2` happens on process 0 after it sent `x1`, but nothing about it reached anyone: it is concurrent with `z1`.

## Level 3: Concurrent writes

Now each process is a *replica*: a copy of the same key-value store, kept on its own machine so that it can answer when the others cannot be reached. A process writes to its own copy, and a message carries everything its sender knows to the receiver. Two replicas can then write the same key without knowing of each other. Keeping only the write with the latest wall clock would silently lose one of the two values, and the wall clocks cannot be trusted anyway. Instead, the store keeps both versions, called *siblings*, until a later write that has seen both replaces them, for example a shopping cart that merges two carts into one.

- `write(process, event, key, value, wall)`: a local event that also writes `value` under `key` at that process. It returns the Lamport timestamp, like `local`, and is refused in the same cases.
- `read(process, key)`: the values of the siblings of `key` at that process, sorted. A value appears once per sibling, so two siblings that hold the same value give it twice. `[]` when `process` is out of range or knows of no write to `key`.
- `concurrentWrites(key)`: every pair of writes to `key` that are concurrent, among all the writes recorded, as `[first, second]` with `first` before `second` by name; the pairs sorted by `first`, then by `second`.

**Which writes a process knows of.** The current vector of a process is the vector of its latest event, or all zeros when it has none. A process knows of a write when the write's vector is `≤` its current vector: the write is its latest event, or happened before it. Messages carry knowledge, so a process can know of a write it never received directly.

**Siblings.** Among the writes to `key` that the process knows of, a write is *superseded* when another of them, to the same key, happened after it. The siblings are the writes that are not superseded. A new write at a process happens after every write that process knows of, so it supersedes them all, but only them: a sibling it has not heard of survives.

### Example 1

<!-- case: ex5 -->

`w1` and `w2` write the cart on two processes that know nothing of each other. Process 0 first reads only its own `apple`. After it receives a message from process 1, it knows of both, and neither happened after the other, so it reads two siblings. Process 1 still knows only `pear`. `w3` on process 0 has seen both and replaces them, but process 1 has not heard of `w3` and still reads `pear`. The concurrent pair `w1`, `w2` stays in the history.

### Example 2

<!-- case: ex6 -->

Three processes write `k`. Process 2 hears of `red` before it writes `green`, so `green` supersedes `red`, but not `blue`, which process 2 has not heard of. When process 1 hears from process 2, it knows of all three writes: `red` is superseded by `green`, and `blue` and `green` are siblings. Process 0 never heard of anything but its own `red`. The concurrent pairs are `a` with `b` and `b` with `c`; `a` happened before `c`.

## Level 4: Hybrid logical clocks

Lamport timestamps and vectors capture causality, but they are counts: a timestamp of `5` says nothing about when something happened, so you cannot ask for "the state as of 10:00". Physical clocks say when, but they break causality. A *hybrid logical clock* (Sandeep Kulkarni and others, 2014) gives every event a pair `(l, c)`: `l` stays close to physical time and `c` is a small counter that keeps causality when `l` alone cannot.

**The rules,** with `pt` the event's `wall` reading. Every process starts with `l = 0` and `c = 0`.

1. A local event, a send or a write: let `old = l`. Set `l = max(old, pt)`. If `l == old`, then `c = c + 1`; otherwise `c = 0`.
2. A receive of a message stamped `(lm, cm)`: let `old = l`. Set `l = max(old, lm, pt)`. Then, checking the cases in this order:
   - if `l == old` and `l == lm`: `c = max(c, cm) + 1`;
   - else if `l == old`: `c = c + 1`;
   - else if `l == lm`: `c = cm + 1`;
   - else `c = 0`.
3. The event's stamp is the new `(l, c)`, and a send puts it into its message.

Pairs compare by `l` first and then by `c`. The paper proves that if `a → b`, then the pair of `a` is smaller than the pair of `b`, and that `l` is never below the event's own reading `pt`. More than that, `l` is the largest physical reading among the event and all the events that happened before it, so `l - pt` measures how far ahead of this process's clock some clock it has heard from was running. When all clocks stay within some error `ε` of each other, `l - pt` stays within `ε` too, which is the sense in which the hybrid clock stays close to physical time. A Lamport timestamp has no such relation to physical time at all.

Every event of every level gets a pair, starting from the first event of the history.

- `hlc(event)`: the event's pair as `[l, c]`.
- `hlcOrder()`: the names of all recorded events, ordered by `l`, then by `c`, then by process number.
- `maxOffset()`: the largest `l - pt` over all recorded events, `0` when there are none.

### Example 1

<!-- case: ex7 -->

Process 1's clock runs about 40 ms ahead. `a1` gets `[100, 0]` from its reading, and `b1` gets `[140, 0]`. When process 0 receives `b1` at its reading `101`, `l` becomes the message's `140`, so `c` continues the message's counter: `[140, 1]`. At `102` its clock is still behind `140`, so `l` stays and `c` counts up: `[140, 2]`. At `141` its own clock has caught up and passed, so `l` follows it and `c` resets to `0`. The largest `l - pt` is `140 - 101 = 39`, about how far the clocks disagree.

### Example 2

<!-- case: ex8 -->

Three events at reading `50` on process 0 count `c` up to `2`. `b1` on process 1 also reads `50` and gets `[50, 0]`. When `a4` receives it, its own `l`, the message's `l` and the clock all agree on `50`, so `c` becomes the larger counter plus one: `max(2, 0) + 1 = 3`. Process 0's clock then reads `49`, behind its `l`, and `c` keeps counting. Process 1 receives `a5` when its clock reads `60`, ahead of everything, so `l` takes the reading and `c` resets.

## Constraints

- `1 <= processes <= 30`
- At most 2,000 calls per test, of which at most 1,000 record an event.
- Names of events and keys: 1 to 20 printable ASCII characters (codes 33 to 126). Values: 0 to 20 printable ASCII characters (codes 32 to 126).
- `0 <= wall <= 10^12`
- Every timestamp, counter and vector entry is at most the number of recorded events.

## Follow-ups

- A vector has one entry per process. What happens to its size when processes join and leave for good, and what would you need to know before dropping an entry?
- `read` here compares every pair of writes to a key. How would a replica keep only the current siblings of each key, and update them when a message arrives with a version it may or may not have seen?
- With hybrid clocks, one process whose clock is far ahead pulls every `l` it reaches forward. How would you refuse a message whose `l` is too far ahead of your own clock, and what would that cost?
- Hybrid pairs can stand in for physical timestamps in a database snapshot: "every write with a pair below `(t, 0)`". Why is that snapshot consistent, when one taken by reading each machine's clock at `t` is not?

## Hints

### Hint 1

Keep two kinds of record. For each process: the current value of its clock. For each event: what it was stamped with, which process it ran on and whether it was a send. Every event method then reads the process's clock, updates it by the rule of its kind, and stores a copy in the event's record. Questions only read the records.

### Hint 2

A receive needs the stamp of the message, and the message is named after its send event, so look the send event up by name. Check everything that can refuse the call before you change any clock, and only then mark the message as received.

### Hint 3

To order the events, sort them by a pair of keys: the timestamp first, and then the process number as a number. Sorting by name, by the order of the calls or by the wall readings gives a different order on a tie or on clocks that disagree.

### Hint 4

A vector event stores a copy of the vector. If you store the process's own list and change it later, every event of that process changes with it. In `compare`, test `≤` in both directions: one direction is `"before"`, the other is `"after"`, and neither is `"concurrent"`. Handle unknown names first, and only then the same name twice.

### Hint 5

For `read`, take the process's current vector, keep the writes to the key whose vectors are `≤` it, and drop each one whose vector is `≤` the vector of another write in that set. Sort the values of what is left, keeping repeats.

### Hint 6

The receive rule of the hybrid clock has four cases, and the first one needs both equalities: when the process's old `l`, the message's `l` and the new `l` are all equal, `c` becomes `max(c, cm) + 1`. Then `l == old` alone gives `c + 1`, `l == lm` alone gives `cm + 1`, and a new `l` that comes from the physical reading gives `0`. Write the local rule and the receive rule as one helper each, called by every event method, so that `write` and `send` cannot drift apart from `local`.
