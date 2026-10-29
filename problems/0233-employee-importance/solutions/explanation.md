# Employee Importance: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| lookup-by-scan | brute | O(n^2) | O(n) | there are only a handful of records, or as a correctness oracle |
| map-and-traverse | optimal | O(n) | O(n) | default answer |

## Approach: lookup-by-scan (Find each employee's record by scanning the list)

### Intuition

Walk the group below the queried employee. Records are in no particular order, so finding the record of an id means scanning the list for it.

### Algorithm

1. Put `employeeId` on a stack and set `total = 0`.
2. Pop an id and scan the list for its record.
3. Add the record's importance to `total` and push its subordinates' ids.
4. Repeat until the stack is empty, then return `total`.

### Correctness

Every employee below the queried one is reached exactly once: each employee has at most one leader and nobody is above themselves, so the group is a tree and no id is pushed twice. The scan finds the record of an id because ids are distinct and every subordinate id has a record. The total is the sum over the group, including the queried employee.

### Complexity

- Time: O(n^2) — up to n records are visited, and each lookup scans up to n records.
- Space: O(n) — the stack can hold up to n ids.

### Trade-offs

No index to build, but quadratic: at n = 5000 the scans alone cost about 1.25 * 10^7 steps. For a few dozen records the difference does not matter.

### Pitfalls and edge cases

- The group includes the queried employee, not only the people below.
- Importance may be negative, so never stop because "nothing more is added".

### Language notes

- Python: `next(record for record in employees if record[0] == wanted)` is the scan.
- TypeScript: `Array.prototype.find` returns `undefined` when nothing matches, hence the cast after a lookup that cannot fail here.
- Java: a small helper scans the `int[][]` and returns the matching row; records are jagged rows, so never assume a length of 2.
- Kotlin: `employees.first { it[0] == wanted }` scans and throws if the id is missing.

## Approach: map-and-traverse (Index the records by id and walk the group with a stack)

### Intuition

Build an id-to-record index once, then traverse the group with a stack. Each lookup is O(1), so the whole traversal is linear.

### Algorithm

1. Build a map from id to record.
2. Put `employeeId` on a stack and set `total = 0`.
3. Pop an id, look up its record, add its importance, and push the ids from index 2 of the record on.
4. Repeat until the stack is empty, then return `total`.

### Correctness

The reachability argument is the same as for the scanning version: every employee below the queried one is visited exactly once, and the map returns the same record the scan would. The sum over the visited records is the total importance.

### Complexity

- Time: O(n) — building the map and visiting each record are both linear; map lookups are O(1) on average.
- Space: O(n) — the map and the stack.

### Trade-offs

The default answer. The traversal is iterative, so recursion depth is no concern (the constraints allow at most 1000 levels, which is safe either way). Answering many queries is better done with one post-order pass that computes every total.

### Pitfalls and edge cases

- Subordinates start at index 2 of a record; index 0 is the id and index 1 the importance.
- Records are jagged: a record without subordinates has length 2.
- Another hierarchy in the same list must be ignored, which the traversal does by only following subordinate ids.

### Language notes

- Python: a dict comprehension builds the index and `list.extend(record[2:])` pushes the subordinates.
- TypeScript: `new Map(employees.map((record) => [record[0], record]))` builds the index.
- Java: `HashMap<Integer, int[]>` plus an `ArrayDeque<Integer>` used as a stack. Totals stay within `int` (at most 10^4 * 100 in absolute value).
- Kotlin: `employees.associateBy { it[0] }` builds the index and `getValue` fails loudly on a missing id.
