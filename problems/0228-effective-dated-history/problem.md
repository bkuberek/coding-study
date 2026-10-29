# Effective-Dated History

## Statement

An insurer keeps a record per contractor (address, class code, payroll basis, status, and so on), and every change has an effective date: the day it becomes true. Changes are often entered late, and some correct earlier entries.

Build `RecordHistory`, which stores every field's values over time. Every call carries `timestamp`, the moment the call is made; timestamps strictly increase from call to call. Values are text, and the empty text `""` means "no value".

There are two kinds of time. An effective date says when a value is true. A timestamp says when the insurer learned it. Level 1 works with effective dates only; Level 2 asks what the insurer knew at an earlier timestamp.

## Input

- `RecordHistory()`: creates an empty history.
- Every method takes `timestamp` first.
- `recordId` names a record and `field` one of its fields; `effectiveDate` and `onDate` are calendar days.
- Each level's section describes the methods it adds and their other parameters.

Each test is a sequence of calls: the constructor first, then the other calls in order.

## Output

One result per call: `null` for the constructor and for `setValue`, a text value for the reads of one field, and a list of `"field=value"` texts for the snapshots. An unknown record or field reads as `""`, or as an empty list for a snapshot, never with an exception.

## Level 1: Effective-dated values

- `setValue(timestamp, recordId, field, effectiveDate, value)`: from `effectiveDate` until the field's next later effective date, the field has `value`. A second write for the same record, field and effective date replaces the first (a correction). Writing `""` means "no value from this date on" (a clear).
- `getValue(timestamp, recordId, field, onDate)`: the value with the latest effective date on or before `onDate`, or `""` when there is none.
- `snapshot(timestamp, recordId, onDate)`: `"field=value"` for every field of the record whose value on `onDate` is not empty, sorted by field name in character-code order. An empty list when there are none.

### Example 1

<!-- case: ex1 -->

The address is `12 Oak St` from 2026-01-01 and `40 Elm Ave` from 2026-06-01. Before the first date there is no value. In March the first address governs, and on 2026-06-01 itself the second one does.

### Example 2

<!-- case: ex2 -->

A snapshot lists the non-empty fields in name order: `classCode` before `name` before `status`. The status is cleared from 2026-09-01 with `""`, so it drops out of the snapshot from that day on. Before every effective date, the snapshot is empty.

## Level 2: As known at a time

- `getValueAsKnown(timestamp, recordId, field, onDate, knownAt)` and `snapshotAsKnown(timestamp, recordId, onDate, knownAt)`: the answers of `getValue` and `snapshot`, computed from only the `setValue` calls made at or before time `knownAt`, as if the later ones had not happened yet.
- `knownAt` may be earlier than every call, or later than the current one.

### Example 1

<!-- case: ex3 -->

The class code `5403` was entered at time 1, and a correction to `5645` for the same effective date at time 5. As known at time 4 the code is still `5403`; as known at time 5 it is `5645`, and the plain `getValue` shows the latest knowledge.

## Constraints

- At most 2000 calls per test.
- `1 <= timestamp <= 10^9`, strictly increasing within a test; `0 <= knownAt <= 10^9`.
- `recordId` is 1 to 20 characters of `[a-z0-9-]`. `field` is 1 to 20 characters: a lowercase letter followed by letters and digits.
- `value` is 0 to 40 printable ASCII characters.
- Dates fall between `2000-01-01` and `2100-12-31`.

## Follow-ups

- A field's whole timeline as known at a time.
- Who made each change.
- Compact history older than a retention date.
- As-known reads in O(log w): sort each field's writes by effective date and timestamp, or keep persistent sorted maps.

## Hints

### Hint 1

Keep one history per record and field.

### Hint 2

Level 1: a sorted list of effective dates per field; a write on an existing date replaces its value.

### Hint 3

Level 2: also keep every write in timestamp order. The writes known at `knownAt` are a prefix of that list.
