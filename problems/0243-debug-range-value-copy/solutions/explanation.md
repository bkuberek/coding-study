# Debug: Range Value Copy: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| index-in-place | optimal | O(n + e) | O(n) | default answer: range over indexes and update `accounts[i]` |

## Approach: index-in-place (Update the slice element through its index)

### Intuition

In `for _, acct := range accounts`, `acct` is not the element. It is a new variable that receives a *copy* of the element on each iteration. `account` is a struct, a value type, so the copy has its own `balance` and `expired`. The cap loop sets both fields on the copy, and the copy is discarded at the end of the iteration. The slice never changes, so every statement shows the uncapped balance and 0 expired points.

The reviewers were right that the comparison and the assignments are correct; the bug is the variable they assign to. The earnings loop works because it writes `accounts[member].balance`, an index expression that names the element itself.

### Debugging approach

1. **Narrow the symptom.** Members below the cap are right; every member above it is wrong, and wrong in the same way: the balance is the uncapped one and nothing expired. The cap step runs, or appears to, without any effect.
2. **Print inside and after the loop.** Inside the loop, after the assignments, `acct` shows the capped values. Right after the loop, `accounts` shows the old ones. Values that are right inside a loop and lost after it point at a copy.
3. **Compare addresses.** `fmt.Println(&acct == &accounts[i])` (with the index from the range) prints `false`: `acct` lives at its own address. A debugger shows the same: setting a field on `acct` leaves `accounts[i]` unchanged.
4. **Compare with the working loop.** The earnings loop indexes the slice, the cap loop does not. Fix the cap loop the same way.

### Algorithm

1. Create one `account` per member with its opening balance.
2. For each earning `[member, points]`, add `points` to `accounts[member].balance`.
3. For each index `i`, take `acct := &accounts[i]`. If `acct.balance > limit`, set `acct.expired = acct.balance - limit` and `acct.balance = limit`.
4. Build the statement: `[balance, expired]` for each account, in order.

### Correctness

`&accounts[i]` points at the element in the slice's backing array, so the assignments in step 3 change the element itself, and step 4 reads the changed values. Every member is visited once in step 3. A member above the limit ends with exactly `limit` points and `expired = balance - limit` (the excess); a member at or below it keeps its balance and the zero `expired` it was created with. The largest possible balance is 10^6 + 10^4 * 10^5, about 1.001 * 10^9, which fits the `int` the encoder range-checks to 32 bits.

### Complexity

- Time: O(n + e) — one pass over the n members per loop and one over the e earnings.
- Space: O(n) — the accounts and the statement.

### Trade-offs

Taking `&accounts[i]` keeps the loop body as it was and makes every write go to the element. Writing `accounts[i].balance` in each statement works too but repeats the index four times. Storing pointers (`[]*account`) would make the original loop correct, since copying a pointer still points at the same struct. It costs an allocation per member and makes every other loop share mutable state, a bigger change than the bug deserves. A functional style, building each statement line from a computed value without mutating `accounts`, avoids the question entirely and is a fine rewrite.

### Pitfalls and edge cases

- The general trap: the value variable of `for ... range` over a slice or an array is a copy of the element. Assigning to it, or to its fields, never changes the slice.
- The same holds for maps: `for k, v := range m` copies the value, and `m[k].field = x` does not even compile for a struct value. Read, modify and store back (`v := m[k]; v.field = x; m[k] = v`), or store pointers.
- Calling a method with a pointer receiver on the copy (`acct.applyCap(limit)`) also changes only the copy. It compiles, because the copy is addressable.
- A balance exactly at the limit is not above it: nothing expires (`h6`). A limit of 0 expires every point (`h4`).

### Prevention

- Use `for i := range s` whenever the loop body writes to the element, and keep `for _, v := range s` for loops that only read.
- No standard tool reports this assignment: `go vet` is silent, and neither `staticcheck` nor `ineffassign` flags writes to fields of the range variable. A test that checks the result of the loop is the guard.
- For larger structs, `gocritic`'s `rangeValCopy` check flags loops that copy big elements, which also nudges code toward indexing.

### Language notes

- Go only. In Java, Kotlin, Python and TypeScript, the loop variable of a for-each over a list of objects is a reference to the object, so assigning its fields changes the element. Copies there are explicit (`copy()`, `clone()`, `{...obj}`), so the shipped loop would have worked.
- Go 1.22 made each iteration's loop variable a new variable, which fixed closures and goroutines capturing one shared variable. The value is still a copy of the element, so this bug is unchanged.
- Rust would not let this compile silently: `for acct in accounts.iter()` gives shared references, and assigning a field through one is a compile error; `iter_mut()` gives mutable references to the elements.
