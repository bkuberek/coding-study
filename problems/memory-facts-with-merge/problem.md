# Memory Facts with Merge

## Statement

An assistant remembers facts about the people it talks to, such as the city someone lives in or the name of their dog, and reads them back into its context in later conversations. Build `FactMemory`, the store behind that memory. Each user has their own facts, and a fact says that a `subject` has an `attribute` with a `value`: subject `home`, attribute `city`, value `lisbon`.

The API grows over four levels. Every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

Every method takes the current time as its first argument, `timestamp`. Nothing reads a clock: time is whatever the caller passes.

Pace yourself over the 90 minutes: read for the first 5, then aim to pass level 1 by minute 20, level 2 by minute 40, level 3 by minute 65 and level 4 by minute 88.

## Input

- `FactMemory()`: creates an empty store.
- `timestamp`: the time of the call. Within one test, timestamps never decrease, and consecutive calls may share one, as when two devices write in the same second.
- `user`: whose facts the call reads or writes. A user nobody has written to has no facts.
- `subject`, `attribute`: which fact. Together they name one fact of one user.
- Each level's section describes the methods it adds and their other parameters.

## Output

Each method returns what its level describes. A missing value is reported as `""`, an empty list or `0`, never with an exception.

## Level 1: Facts per user

- `remember(timestamp, user, subject, attribute, value)`: stores the fact for `user` and returns its new id. Ids are `f1`, `f2`, `f3` and so on, in the order facts are created, counted over the whole store and not per user. Remembering a subject and attribute again replaces the value, and the new fact gets a new id, even when its value is the same.
- `recall(timestamp, user, subject, attribute)`: the value `user` has for that subject and attribute, or `""` when there is none.
- `listFacts(timestamp, user)`: one entry `"<subject>.<attribute>=<value>"` for each fact `user` has, ordered by subject and then by attribute, in plain string order. An empty list when the user has no facts.

### Example 1

<!-- case: ex1 -->

The second `remember` of `home.city` replaces `lisbon` and gets the next id, `f3`. Nothing was stored under `home.zip`, and `bo` has no facts at all. The list puts `home` before `pet`.

## Level 2: Versions and as-of reads

A replaced fact is not lost: it stays in the history of its subject and attribute, and the newer fact supersedes it. Every fact keeps its id, its value and its **time**, which is the timestamp of the call that remembered it.

- `history(timestamp, user, subject, attribute)`: every fact of that subject and attribute, oldest first, each as `"<id>@<time>=<value>"`. An empty list when there is none.
- `recallAt(timestamp, user, subject, attribute, at)`: the value in force at time `at`, which is the value of the last fact in the history whose time is at most `at`. When several facts share that time, the last of them in the history is the one in force. `""` when every fact is later than `at`, or there is none.
- `recall` and `listFacts` keep reading the last fact of each history.

### Example 1

<!-- case: ex2 -->

At time 0 nothing had been remembered yet. A fact is in force from its own time, so at 4 the city is already `porto`, and still is at 8. `job.title` was remembered at 6, so at 5 it was unknown. `f3` belongs to another subject, so the history of `home.city` skips it.

## Level 3: Merging two stores

The same person may use the assistant on two devices, each kept here as a user of its own, such as `phone` and `laptop`, and the two must come together.

- `setPriority(timestamp, user, priority)`: sets the priority of `user`'s store. A store has priority 0 until it is set.
- `merge(timestamp, fromUser, intoUser)`: brings `fromUser`'s facts into `intoUser` and returns how many facts `intoUser` took. For each subject and attribute of `fromUser`, its current fact (the last of its history) meets `intoUser`'s current fact for the same subject and attribute:
  1. When `intoUser` has none, `intoUser` takes the fact.
  2. Otherwise the fact with the later time wins.
  3. When the times are equal, the fact from the store with the higher priority wins. When the priorities are equal too, `intoUser` keeps its own.
- Taking a fact adds a copy to the end of its history in `intoUser`. The copy gets a new id and the same value, and it keeps the **time of the fact it copies**, because that is when the fact was remembered. So `recallAt` sees the copy from that time on, and a later merge compares that time. When a merge takes several facts, they get their new ids in the order of their subject and then their attribute.
- `fromUser` does not change.

### Example 1

<!-- case: ex3 -->

`porto` was remembered at 2, after `lisbon` at 1, so the phone takes it. The copy gets the new id `f5` but keeps the time 2. The phone had no `pet.name`, so it takes `rex` as well, as `f6`. `diet.type` exists only on the phone and stays. The laptop does not change.

### Example 2

<!-- case: ex4 -->

Both teas were remembered at 7. With equal priorities the phone keeps `green`. Once the laptop has the higher priority, its `black` wins the tie.

## Level 4: Export and import

A store can also be copied to another device, which has ids of its own.

- From this level on, a value may also be a **reference** to another fact of the same user: `@` followed by that fact's id, such as `@f1`. The store keeps it as text, like any other value. `merge` copies it as it is: within one store the ids never change, so a copied reference still names the same fact.
- `exportFacts(timestamp, user)`: every fact in every history of `user`, as one line `"<id> <time> <subject> <attribute> <value>"` each, ordered by the number in the id. An empty list when the user has no facts.
- `importFacts(timestamp, user, lines)`: rebuilds facts from exported lines, which may come from another store, as facts of `user`. When `user` already has facts, it imports nothing and returns an empty list. Otherwise each line becomes a new fact of `user`, in line order:
  - It gets a new id, the next one of this store, as `remember` would give it.
  - It keeps the time, subject and attribute of its line, and goes to the end of its history.
  - A value that is a reference to an id of the lines becomes a reference to the new id of that line's fact. The line it names may come before or after its own. Any other value is kept as it is.

  It returns the new ids in line order.
- The lines always follow the format of `exportFacts`. Their ids are distinct, every reference in them names an id of the lines, every time is at most `timestamp`, and the lines of one subject and attribute come in history order.

### Example 1

<!-- case: ex5 -->

The export holds every fact, the replaced `lisbon` included, which `trip.origin` refers to. In this store `f1` to `f3` are taken, so the tablet gets `f4` to `f6`, and the reference to `f1` becomes a reference to its copy, `f4`. The imported facts keep their times, and the next new fact is `f7`.

## Constraints

- At most 1000 calls per test.
- `1 <= timestamp <= 10^9`, never decreasing within a test.
- Users, subjects, attributes and values are 1 to 10 lowercase letters or digits.
- `0 <= at <= 10^9` and `0 <= priority <= 100`.
- At most 200 lines per import.

## Follow-ups

- Two devices write while offline, and neither clock can be trusted. What could replace "the later time wins"?
- A user asks the assistant to forget a fact for good. What has to go, so that no history, merge or import brings it back?
- Importing the same lines twice, into two users and then merging them, makes copies of copies. How would you recognize a fact that is already there?

## Hints

### Hint 1

Route every read through one helper that finds the fact in force at a given moment. `recall` is then that helper at the end of time.

### Hint 2

A copy has two numbers that must not be confused: its own new id, and the time of the fact it copies.

### Hint 3

For the import, give out every new id in a first pass over the lines, then rewrite the references in a second pass. Compare whole ids, never a piece of a line's text.
