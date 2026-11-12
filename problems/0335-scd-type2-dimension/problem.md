# SCD Type 2 Dimension

## Statement

Build `DimensionTable`, the table that a data warehouse keeps about the *things* its events refer to: customers, products, stores. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**What is a dimension?** A warehouse splits its data in two kinds of table. A *fact* table records events, one row each: an order, a payment, a page view, with numbers you can add up (an amount, a quantity). A *dimension* table describes who or what took part: one row per customer with the customer's name, city and email. Reports join the two, "revenue by city" for example, by looking up the dimension row of each fact.

**Business keys and surrogate keys.** The source system that sends you customers already names each one, with a code such as `C1042`. That code is the *business key*: it belongs to the source, and it stays the same while the customer's details change. The warehouse gives every row it stores a number of its own, the *surrogate key*: `1`, `2`, `3`, and so on. Facts point at that number, not at the business key. You will see why at level 2: one customer can end up with several rows over time, and each row needs a name of its own.

**Loads.** The source sends its rows in batches, each with the date it describes. A date is an integer written as `YYYYMMDD`, so `20260315` is 15 March 2026. Dates are only compared, as numbers, and never added to: the problem needs no calendar.

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 30, level 2 by 60, level 3 by 85 and level 4 by 115, keeping the last minutes for a final run.

## Input

- `DimensionTable(attributes)`: creates an empty dimension. `attributes` names the columns that describe each thing, in order, such as `["name", "city", "email"]`.
- A **source row** is a list of strings: the business key first, then one value for each attribute, in the order of `attributes`. A value may be the empty string.
- A **date** is an integer `YYYYMMDD`, compared as a number.
- Each level's section describes the methods it adds and their parameters.

## Output

A stored row is returned as a list of strings, always in this shape:

`[surrogateKey, businessKey, value1, ..., valueN, validFrom, validTo, current]`

Numbers are written in decimal (`"7"`, `"20260315"`). `validFrom` and `validTo` are the dates the row is valid between, and `current` is `"Y"` or `"N"`. A method that finds nothing returns `-1` for a number and `[]` for a list. Text is ordered by the numeric value of its characters, so that `B` comes before `a`, and `10` before `9`.

## Level 1: Surrogate keys

- `load(rows, loadDate)`: applies a batch of source rows that describes the source on `loadDate`, and returns three counts `[inserted, changed, unchanged]`.
  - When a business key appears more than once in a batch, its **last** row counts and the earlier ones are ignored. Each business key of the batch is counted once.
  - A business key the dimension has never seen is **inserted**: it gets a new row with the next surrogate key, `validFrom = loadDate`, `validTo = 99991231` and `current = "Y"`.
  - For a known business key, the row's values are compared with the incoming ones, exactly, character by character. If all are equal the key is **unchanged**. Otherwise it is **changed**, and at this level every changed value is overwritten in place: the row keeps its surrogate key and its `validFrom`.
- **Surrogate keys** start at `1` and are never reused. Within one batch, the business keys that need new rows get their numbers in the order of the business keys, by character code, whatever the order of the rows in the batch. The next batch continues after the largest number given so far.
- `lookup(businessKey)`: the surrogate key of the key's current row, or `-1`.
- `rowOf(surrogateKey)`: the stored row with that surrogate key, or `[]`.
- `size()`: the number of stored rows.

Load dates never go down at levels 1 to 3: each load is dated on or after the one before it.

`99991231` is the *open end*: a date later than any real one, which says "valid until further notice". At this level every row is current and open; level 2 closes rows.

### Example 1

<!-- case: ex1 -->

The first batch lists `C2` before `C1`, but `C1` gets surrogate key `1` because it comes first in character order. In the second batch `C1` moves to Lyon: the change overwrites its row, which keeps key `1` and its start date. `C3` is new and gets key `3`, and `C2` arrives with the same values, so it is unchanged.

### Example 2

<!-- case: ex2 -->

`k2` appears twice in the first batch: the second row, `bronze`, is the one stored, and `k2` counts as one inserted key. In the second batch the last row of `k1` says `silver`, so `k1` changes even though its first row repeated the stored value.

## Level 2: Type 2 history

Overwriting loses the past. If a customer moves from Paris to Rome, every old order now looks as if it was placed from Rome, and "revenue by city last year" is wrong. A **type 2** attribute keeps its history: a change does not overwrite the row, it closes the row and adds a new one, a new **version** of the same business key. Attributes that are not tracked stay **type 1**: they keep no history, and a change simply corrects them.

- `trackHistory(attribute)`: makes `attribute` a tracked (type 2) attribute, for the loads after the call; rows already stored stay as they are. It returns `true`, or `false` when `attribute` is not one of the dimension's attributes or is tracked already. Before any call, no attribute is tracked.
- `history(businessKey)`: every version of the key, ordered by `validFrom`; `[]` for an unknown key.

A version is valid from `validFrom` up to but **not including** `validTo`: the half-open interval `validFrom <= date < validTo`. The versions of a key never overlap, and when one is closed it ends exactly where the next one starts. When a load changes a known key:

- **A tracked attribute changed.** Close the current version: `validTo = loadDate` and `current = "N"`. Then add a new version with the next surrogate key, all the incoming values, `validFrom = loadDate`, `validTo = 99991231` and `current = "Y"`.
- **The current version started on `loadDate`** (a second batch on the same date): a closed version from that date to that date would hold no date at all, so the tracked values are overwritten in the current version instead, and no version is added.
- **An untracked attribute changed.** It keeps one value per business key, the latest: the new value is written into **every** version of the key, closed ones included, also when a tracked attribute changes in the same row.

A key whose row changed in any of these ways counts as changed, once. Within one batch, new versions of known keys and the rows of new keys share one numbering, in the order of the business keys.

### Example 1

<!-- case: ex3 -->

`city` is tracked; `name` and `email` are not. Moving to Rome on 1 March closes the Paris version on `20260301` and adds version `2` from that date. An email change on 1 April is untracked, so both versions now show the new address, and no version is added.

### Example 2

<!-- case: ex4 -->

The second load is on the same date as the first, so `Bergen` overwrites `Oslo` in place. On 20 January only the name changes, in place. On 30 January the city and the name change together: a new version starts, and the closed one shows the new name too.

## Level 3: Point in time and facts

A report about last March needs the customer as they were in March. Because every version has its dates, the dimension can answer "which version was valid then".

- `lookupAt(businessKey, asOf)`: the surrogate key of the version with `validFrom <= asOf < validTo`, or `-1` when there is none (an unknown key, or a date before the key's first version).
- `snapshotAt(asOf)`: the dimension as it was on `asOf`: for each business key, its version valid on that date, if any, ordered by business key.
- `resolveFacts(facts)`: finds the surrogate key for each incoming fact. A fact is `[factId, businessKey, eventDate]`, the date written as decimal digits. The answer has one row `[factId, surrogateKey, status]` per fact, in the order of `facts`:
  - `"unknown-key"`, with surrogate key `"0"`, when the dimension has never seen the business key;
  - `"no-version"`, with `"0"`, when the key is known but no version is valid on the event date;
  - `"current"` when the version valid on the event date is the current one;
  - `"late"` when it is an older, closed version: the fact arrived after its customer had already changed.

Surrogate key `0` is the conventional *unknown member*: facts that cannot be matched still get a key, so they are never dropped from totals, and they are easy to find and fix later. `0` is never given to a stored row, so `rowOf(0)` is `[]`.

### Example 1

<!-- case: ex5 -->

`C1` lived in Paris from 1 January and in Rome from 1 March. On 28 February the Paris version is valid; on 1 March, the first day of the Rome version, it is the Rome one. The fact dated 10 February belongs to the Paris version, which is closed, so it is late. `C9` was never loaded, and nothing was valid for `C1` in December 2025.

### Example 2

<!-- case: ex6 -->

On 15 February the snapshot holds `C1` in Paris and `C2`; `C3` did not exist yet. On 1 March `C1` is in Rome. Before the first load the snapshot is empty.

## Level 4: Late changes and deletes

Real sources are messy. A batch can arrive late, describing a date before rows you have already loaded, and a business key can disappear from the source.

`load` now accepts any date. For each business key of the batch, in business key order:

1. **Untracked values** come from the latest-dated load of the key. If `loadDate` is on or after the date of every earlier load that carried the key, the untracked values are applied as at level 2 (an equal date is a later call, so it wins). Otherwise the row is older news and its untracked values are ignored.
2. **Tracked values** are placed in time. Find the version valid on `loadDate`:
   - It exists and its tracked values equal the incoming ones: nothing to do.
   - It exists, differs, and starts on `loadDate`: overwrite its tracked values in place.
   - It exists, differs, and starts before `loadDate`: **split** it. The old version now ends on `loadDate`, and a new version runs from `loadDate` to where the old one used to end. The new version is current exactly when the old one was. A late change is therefore a version in the middle of history, and the current version stays as it is.
   - No version is valid on `loadDate` (the date falls before the first version, or after the key was closed): add a version from `loadDate` up to the start of the next version of the key, or to the open end when there is none.

A new version takes the incoming tracked values and the key's untracked values. Versions are never merged, even when two neighbours end up with equal values. A key counts as changed when anything stored about it changed.

- `loadFull(rows, loadDate)`: a batch that lists **every** business key the source has on `loadDate`. It applies `rows` as `load` does, then **closes** every business key that is missing from the batch and still has a current version: that version gets `validTo = loadDate` and `current = "N"`. This is a *soft delete*: the rows stay, so old facts keep their keys and history stays true. It returns `[inserted, changed, unchanged, closed]`. A full load is dated after every earlier load.
- A closed key has no current version, so `lookup` returns `-1`. When it comes back in a later batch, it gets a new version as described above, with a new surrogate key; the closed version is never reopened.
- `fullHistory()`: every stored row, ordered by business key, then by `validFrom`.

This is how SQL:2011 treats rows with an application-time period: periods are closed-open, and an update for part of a row's period splits the row into contiguous pieces.

### Example 1

<!-- case: ex7 -->

`C1` moved to Rome on 1 June, and a late batch then says it lived in Lyon from 1 March. The Paris version is split at 1 March, and the Lyon version, key `3`, runs from 1 March to 1 June, where Rome starts. The current Rome version is untouched. History is ordered by date, so key `3` sits between `1` and `2`. A later batch dated 1 April renames Ann, but a load dated 1 June already carried `C1`, so the old name is ignored, and the city matches the Lyon version: nothing changes.

### Example 2

<!-- case: ex8 -->

The full load of 1 July lists `C3` and `C1`, who moved to Nice; `C2` is missing, so its version is closed on `20260701` and `lookup` finds no current row. A fact on 5 July finds no version. When `C2` comes back on 1 August it gets a new version, key `5`, and the gap between 1 July and 1 August stays empty.

## Constraints

- `1 <= attributes.length <= 6`, distinct names of lower-case letters and `_`.
- Business keys are 1 to 20 printable ASCII characters (codes 33 to 126); values are 0 to 30 printable ASCII characters (codes 32 to 126).
- Every source row has exactly `1 + attributes.length` strings; every fact has three, the third a date.
- Dates are integers from `19000101` to `99991230`.
- At most 200 calls per test, and at most 100 rows or facts per call.

## Follow-ups

- Facts loaded before a late change still point at the version that was valid when they were loaded. How would you find the facts whose key a later split makes wrong, and restate them?
- A fact can arrive for a customer the source has not sent yet. Instead of the unknown member, some warehouses insert a placeholder row and fill it in when the real row arrives. What changes in `load` for such a row?
- Keeping one value per key for untracked attributes rewrites every version on each correction. When is it better to keep a separate "current value" column next to the historical one?
- Real loads compare a hash of the tracked columns instead of each value. What would you hash, and how would you keep two languages' hashes equal?

## Hints

### Hint 1

Start with two maps. One goes from business key to the key's rows, the other from surrogate key to a row. A counter gives the next surrogate key. Before you touch any row, reduce the batch to one row per business key (a map does this: later rows overwrite earlier ones), then sort the business keys and walk them in that order.

### Hint 2

Store a row as a small record: surrogate key, business key, a list of values, `validFrom` and `validTo`. The `current` flag does not need to be stored, since a row is current exactly when its `validTo` is the open end.

### Hint 3

At level 2, keep the rows of each business key in a list sorted by `validFrom`. The current row is the last one. A tracked change sets the last row's `validTo` and appends; an untracked change loops over the whole list.

### Hint 4

At level 3, "the version valid on a date" is the last version whose `validFrom` is at or before the date, provided the date is before its `validTo`. On a sorted list, a binary search finds it.

### Hint 5

At level 4, insert new versions into the sorted list at the place their `validFrom` gives, instead of appending. Remember, per business key, the latest date of a load that carried it: an incoming row may overwrite untracked values only when its date is at least that one.

### Hint 6

For a split, copy the old version's end into the new version before you shorten the old one. When no version is valid on the load date, the next version is the first one in the sorted list whose `validFrom` is after the load date.
