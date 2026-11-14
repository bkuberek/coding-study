# CRDT Replicas

## Statement

Build `Replicas`, a small simulation of several copies of the same data. Each copy accepts changes on its own, without asking the others first, and now and then one copy passes what it knows to another. Your job is to make sure that the copies never end up disagreeing for good: once two copies have heard about the same changes, they hold the same data, whatever order the news reached them in. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working.

**What is a replica?** A replica is one copy of some shared data, kept on one machine. Applications keep several replicas so that each user works with a copy close by, and so that the data survives when one machine is down or offline. Think of a shared shopping list on a phone and on a laptop: each device holds its own replica of the list.

**Why do replicas disagree?** Each replica accepts changes immediately, even while it cannot reach the others. That is the whole point: the phone keeps working on a train with no signal. But it means two replicas can change at the same time, and for a while each one knows something the other does not. Example: a post has no likes. On the phone, 3 people like it; on the laptop, 2 other people like it. The phone shows 3, the laptop shows 2, and the true answer, 5, is on neither device yet.

**What does merge mean?** Sooner or later the devices reconnect, and one replica sends its state to another. Merging is what the receiving replica does with it: it combines what it already has with what arrived, so that afterwards it knows everything both of them knew. In the example, after the laptop merges the phone's state, it should show 5.

**Why must merge not care about order?** The network decides when and how often states arrive. A state can arrive late, after newer news has come another way; it can arrive twice; three replicas can exchange states in any order. If the result of merging depended on any of that, replicas would drift apart for good. So merging has to give the same answer whatever the order, however the merges are grouped, and however many times the same state is merged. The obvious ideas fail this test. If each replica keeps one number and a merge keeps the larger one, the laptop ends with 3: two likes are lost. If a merge adds the two numbers, the laptop gets 5, but when the same state arrives a second time it gets 8. Part of the problem is finding what a replica must keep so that merging is safe.

Data types built this way are called conflict-free replicated data types, or CRDTs: every replica can be changed at any time, merging never needs a decision from outside, and replicas that have heard about the same changes hold the same state.

**How the class works.** `Replicas(ids)` creates one empty replica for each id. Every method names the replica it acts on. A change happens at one replica only, and nothing travels by itself: replicas learn about each other's changes only through `merge` (and, at level 4, `sync`). A replica has **seen** a change when the change was made at that replica, or when a merge or a sync brought it from a replica that had seen it. Every query answers from what the queried replica has seen, and the rules of each level say exactly how.

Aim to finish in 90 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 30, level 2 by 45, level 3 by 65 and level 4 by 85, keeping the last minutes for a final run.

## Input

- `Replicas(ids)`: creates one empty replica per id. Ids are distinct.
- `replica`, `source` and `target` are always ids given to the constructor, and `source` and `target` always differ.
- Counters, registers and sets have names, and the three kinds of names are separate: a counter and a register may share a name. A name that was never used holds nothing yet.
- Each level's section describes the methods it adds and their parameters.

## Output

Queries return what the queried replica has seen. `merge` returns nothing; every other method returns the value its level describes.

## Level 1: Counters that merge

A counter is a whole number that replicas can raise and lower.

- `increment(replica, counter, amount)`: the replica adds `amount` to the counter. Returns the counter's value at that replica afterwards.
- `decrement(replica, counter, amount)`: the replica subtracts `amount` from the counter. Returns the counter's value at that replica afterwards. Values may go below zero.
- `value(replica, counter)`: the counter's value at that replica: the sum of the amounts of every increment of that counter the replica has seen, minus the sum of the amounts of every decrement of it the replica has seen. A counter the replica has seen no change of has value `0`.
- `merge(source, target)`: `target` learns everything `source` has seen, about every counter, and from level 2 on about registers and sets too. `source` does not change. Merging can happen in any order and any number of times: `target` only ever gains changes it had not seen.

### Example 1

<!-- case: ex1 -->

Replicas `a` and `b` count likes on their own: `a` has seen 3 and `b` has seen 2. After `merge(b, a)`, `a` has seen both increments and shows 5; after `merge(a, b)`, so does `b`. Merging `b` into `a` a second time brings nothing new, so `a` still shows 5.

### Example 2

<!-- case: ex2 -->

`a` adds 10 to `stock` and both other replicas learn it. Then `b` takes away 3 and `c` takes away 4 at the same time. `a` hears from `b` first and then from `c`; `b` hears from `c` first and then from `a`. Both end with `10 - 3 - 4 = 3`, because they have seen the same three changes.

## Level 2: Last writer wins

A register holds one text, and replicas can overwrite it. When two replicas write different texts at the same time, both texts cannot survive, so the replicas need a rule that every one of them applies the same way: the write with the greater stamp wins.

- `write(replica, register, text, timestamp)`: the replica writes `text` into the register, with the stamp `(timestamp, replica)`. The write takes effect only if the register has no text yet at that replica, or if the write's stamp is greater than the stamp of the text the replica holds. Returns `true` when it took effect, `false` when it was ignored.
- `read(replica, register)`: the text of the register at that replica, or `""` when the replica has seen no write to it.
- `merge(source, target)` now also merges registers: for each register, `target` ends with the text whose stamp is the greater of the two, and with the text from `source` when `target` had none.

**Comparing stamps.** The greater timestamp wins. When the timestamps are equal, the greater replica id wins, comparing ids character by character by their character codes, as the default string comparison of every language here does: `b` is greater than `a`, `ab` is greater than `a`, and digits come before letters. Two writes never share a stamp, because a replica ignores a write that does not beat what it holds, so this order decides every case the same way at every replica. Ignoring such a write departs from the classic last-writer-wins register (Specification 8 of the INRIA report by Shapiro, Preguiça, Baquero and Zawirski), where an assignment always takes effect because its timestamp is assumed to come from a clock consistent with causality; here the timestamps are given, and can be older than what the replica already holds.

So a register shows the text of the greatest-stamped write the replica has seen among those that took effect. The timestamp says when the writer's own clock thought the write happened, and clocks on different machines are rarely in step: the rule picks the highest timestamp, not the write that came last in real time.

### Example 1

<!-- case: ex3 -->

`a` writes `red` at timestamp 10 and `b` writes `blue` at 12. Each replica first sees only its own write. Once they merge, both show `blue`, the write with the greater timestamp, whichever direction the merge went.

### Example 2

<!-- case: ex4 -->

Both writes carry timestamp 5, so the replica ids decide: `b` is greater than `a`, so `light` wins at both replicas. Then `a` writes `dim` at timestamp 4, which is older than the stamp of the text it holds, so the write is ignored; at timestamp 6 it takes effect.

## Level 3: An add-wins set

A set holds distinct elements, and replicas can add and remove them. The hard case is an add and a remove of the same element at the same time on two replicas: this level keeps the element, because the remove could not have meant an add it never saw.

- `add(replica, setName, element)`: the replica adds `element` to the set. Every add is a separate change with its own tag, `"<replica>:<n>"`, where `n` counts the adds made at that replica so far, in all sets together, starting at 1. Returns the tag. Adding an element that is already present is still a new add with a new tag.
- `remove(replica, setName, element)`: the replica removes the element as it sees it: every add of `element` to the set that the replica has seen, and has not seen removed, is now removed. Returns how many adds that removed, `0` when the element was not present (and then nothing changes).
- `contains(replica, setName, element)`: whether the replica has seen an add of `element` to the set that it has not seen removed.
- `elements(replica, setName)`: every element `contains` would answer `true` for, each once, in ascending order of the same string comparison. `[]` for an empty or unknown set.
- `merge(source, target)` now also merges sets: `target` sees every add and every removal of an add that `source` has seen.

Because a remove only covers the adds its replica has seen, an add made elsewhere at the same time survives it, and an element can be added again after it was removed.

### Example 1

<!-- case: ex5 -->

On a single replica the set behaves like an ordinary set. `milk` is added with tag `a:1` and `eggs` with `a:2`; removing `milk` removes one add. Adding `milk` again is a new add, `a:3`, so it is back. Removing `tea`, which is not there, removes nothing.

### Example 2

<!-- case: ex6 -->

`b` learns about the add `a:1` and removes `milk`, which removes that one add. Meanwhile `a`, not knowing, adds `milk` again as `a:2`. After the replicas merge both ways, `a:1` is removed everywhere but `a:2` is not, so `milk` is in the set on both: the add wins over the concurrent remove.

## Level 4: Delta sync

`merge` sends a replica's whole state every time, even when almost nothing changed since the last merge. `sync` sends only what changed since the target last acknowledged the source, and must leave the target in exactly the state a full `merge` would.

**The state as entries.** The state of a replica is made of entries, and every entry can only grow:

- For each counter, one entry for each replica that has added to it (the total that replica added), and one for each replica that has subtracted from it (the total it subtracted). A replica that has done both has two entries for that counter.
- For each register with a text, one entry (the text and its stamp).
- For each add the replica has seen, one entry, and for each add it has seen removed, one more entry.

An entry **changes** when it appears or when its value grows: an increment or decrement raises the replica's own total, a write that takes effect replaces the register's entry, an add creates an entry, a remove creates one entry for each add it removes, and a `merge` or `sync` changes each entry it brings that is new to the target or larger than the target's. An entry that arrives with a value that is not larger changes nothing.

- `stateSize(replica)`: the number of entries in the replica's state, which is what a full `merge` would send.
- `sync(source, target)`: `source` sends `target` every entry of its own that changed since the last `sync(source, target)`, or every entry if there was none, each once with its current value. `target` takes them in exactly as `merge` would, and then acknowledges, so the next `sync(source, target)` starts from here. Returns the number of entries sent.

Each pair of replicas keeps its own acknowledgement, in one direction: `sync(a, b)` does not change what `sync(a, c)` or `sync(b, a)` will send. Entries that changed at the source because they arrived from somewhere else, including from the target itself, count as changed too, and an entry that changed several times since the last acknowledgement is sent once. `merge` does not change any acknowledgement.

### Example 1

<!-- case: ex7 -->

`a` holds four entries: its totals for `likes` and `views`, the register `title` and the add `a:1`. The first sync sends all four. After one more increment of `views`, only that entry has changed, so the second sync sends 1 entry while a full merge would still send 4, and `b` shows the same value a merge would give. A third sync has nothing to send.

### Example 2

<!-- case: ex8 -->

Three increments change one entry, `a`'s total for `n`, so the first sync sends one entry holding 3. `b` has never synced to `a`, so `sync(b, a)` sends every entry of `b`: the total of `a`, which `b` received, and `b`'s own subtracted total. Then nothing is left to send.

## Constraints

- `1 <= ids.length <= 8`.
- Ids, names, elements and texts are 1 to 10 characters, each a lowercase letter, a digit or `-`.
- `1 <= amount <= 1000`, and every counter value stays within `-10^6` and `10^6`.
- `1 <= timestamp <= 10^12`.
- At most 300 method calls per case.

## Follow-ups

- Every removed add leaves an entry behind for ever, so the set never shrinks. When would it be safe to forget a removed add, and what would a replica need to know about the others first?
- Two writes at the same time lose one of them silently. How would a register that keeps both concurrent texts, and lets the reader choose, work, and what would it need to tell "at the same time" from "one after the other"?
- The timestamp here comes from the writer's clock. What goes wrong when a clock runs behind, and what kind of clock would make every write that happened after another one carry a greater timestamp?
- `sync` sends back to `b` entries that `b` itself sent. What would the source need to remember to leave those out, and is the saving worth it?
- A replica that crashes and forgets its acknowledgements can always fall back to sending its whole state. Why is that always safe here?
- The counter keeps one entry per replica that ever changed it. What would you do when replicas join and leave over time?

## Hints

### Hint 1

Think of a merge as "learn what the other replica knows". Learning the same thing twice must change nothing, and learning A and then B must leave you where B and then A would. Before writing code, try it on paper with two replicas that each count on their own and one number each: see what "keep the larger number" loses and what "add the numbers" counts twice.

### Hint 2

A single number cannot tell you which changes it already includes. Keep the numbers apart by where they came from: if each replica only ever changes its own part, every part only grows, and two copies of the same part can be compared without knowing their history.

### Hint 3

For a register, everything a merge needs is in the stamp, and the greater stamp is the same whichever replica asks. For a set, a remove cannot simply delete the element by name, or it would also delete adds it never saw. Give each add its own identity and decide what a remove records.

### Hint 4

For `sync`, the source needs two things: for each entry, when it last changed at the source, and for each target, how far that target has acknowledged. A counter per replica that goes up on every change gives both: an entry remembers the count at its last change, and an acknowledgement is the count at the time of the sync.

### Hint 5

One design that survives all four levels: per counter, a map from replica id to two totals, up and down, where a merge keeps the larger of each total; per register, the text with its timestamp and writer, where a merge keeps the greater `(timestamp, writer)`; per set, for each element a map from tag to a removed flag, where a merge takes every tag and every removed flag. Give every entry the replica's change count at its last change. `sync(source, target)` joins into the target the entries whose count is greater than `acked[target]`, counts them, and then sets `acked[target]` to the source's current count.
