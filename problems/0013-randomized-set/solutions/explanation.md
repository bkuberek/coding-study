# Randomized Set: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| list-scan | brute | O(n) per op | O(n) | the set stays tiny, or as a correctness oracle |
| hash-set | intermediate | O(1) insert and remove, O(n) getRandom | O(n) | `getRandom` is rare |
| array-and-index-map | optimal | O(1) per op | O(n) | default answer: every operation in O(1) |

Here n is the number of values in the set. Each approach needs two abilities: finding a value (for `insert` and `remove`) and picking a uniformly random position (for `getRandom`). An array is good at the second, a hash table at the first; the optimal approach combines them.

The tests call `getRandom` only on a one-element set, so they cannot detect a biased choice. Uniformity is argued below instead.

## Approach: list-scan (Dynamic array with linear search)

### Intuition

Store the members in a dynamic array. A random index gives a uniform member in O(1). Finding a value needs a scan, but removal can avoid shifting: the order of a set is irrelevant, so the last element can fill the gap.

### Algorithm

1. `insert(value)`: scan the array; if `value` is there, return `false`; otherwise append it and return `true`.
2. `remove(value)`: scan for `value`; if absent, return `false`. Otherwise overwrite its slot with the last element, drop the last slot and return `true`.
3. `getRandom()`: return the element at a uniformly random index in `[0, size)`.

### Correctness

Invariant: the array holds each member exactly once. `insert` appends only absent values; `remove` replaces the removed value by the last element, which is a different member (or the value itself when it was last), and then shrinks the array by one, so every other member still appears once. A uniformly random index then selects every member with probability `1/size`.

### Complexity

- Time: O(n) per op — `insert` and `remove` scan up to n elements; `getRandom` is O(1). Over the generated sequences, the set holds about n/20 values while n calls run, so the whole sequence grows with the square of its length.
- Space: O(n) — one slot per member.

### Trade-offs

Simple and obviously correct, with an optimal `getRandom`; only the search is slow. At 100,000 calls on a set of about 5,000 values it compares about 5 * 10^8 values, against 10^5 hash lookups for the optimal approach.

### Pitfalls and edge cases

- Deleting from the middle with a shifting removal (`list.remove(value)`, `splice`) is a second O(n) cost; swapping with the last element avoids it.
- When the removed value is the last element, overwriting its slot with itself and then dropping it is still correct; the TypeScript and Kotlin references pop first and only write back when the gap is not at the end.

### Language notes

- Python: `value in self.values` and `self.values.index(value)` scan in C; `random.choice` picks a uniform element.
- TypeScript: `includes`, `indexOf` and `pop`; `Math.floor(Math.random() * length)` is a uniform index.
- Java: `values.indexOf(value)` boxes the `int` and calls `indexOf(Object)`, which searches for the value. `values.remove(values.size() - 1)` calls `remove(int)`, which removes by position: the two overloads are a classic `List<Integer>` trap.
- Kotlin: `values.removeAt(values.lastIndex)` removes by position; `values.random()` draws a uniform element.

## Approach: hash-set (Hash set with a walk for getRandom)

### Intuition

A hash set gives O(1) average `insert` and `remove` and reports whether they changed anything. What it cannot do is pick a member at random: it has no positions to index into, so `getRandom` walks the iteration order to a random rank.

### Algorithm

1. `insert(value)`: add to the set; return whether it was absent.
2. `remove(value)`: delete from the set; return whether it was present.
3. `getRandom()`: draw a uniform rank `r` in `[0, size)`, iterate the set and return the `r`-th element.

### Correctness

`insert` and `remove` are the set's own operations with their "changed" result. The iteration order of a set is some fixed sequence of its `size` members, each appearing once; a uniform rank selects each position, and therefore each member, with probability `1/size`.

### Complexity

- Time: O(1) insert and remove, O(n) getRandom — hash operations are O(1) on average; the walk visits up to n elements. The generated sequences call `getRandom` only on a one-element set, so the whole sequence stays linear in the number of calls.
- Space: O(n) — the set.

### Trade-offs

The natural first answer, and fine when random draws are rare. It fails the "every operation in O(1)" requirement, which is the point of the question: the follow-up is how to get random access without giving up hashing.

### Pitfalls and edge cases

- Picking "the first element" of a set is not random: iteration order is deterministic for a given history.
- Converting the set to a list on every `getRandom` call is also O(n) and allocates on every call.

### Language notes

- Python: `islice(self.values, rank, None)` skips `rank` elements of the set's iteration in C, but it is still O(n).
- TypeScript: `Set.delete` returns whether the value was present, which is exactly the result `remove` needs.
- Java: `Set.add` and `Set.remove(Object)` return whether the set changed; `getRandom` advances an iterator `rank` times.
- Kotlin: `elementAt(index)` on a `Set` iterates to the index; it reads like indexing but costs O(n).

## Approach: array-and-index-map (Array plus a map from value to index)

### Intuition

Keep the members in an array, for O(1) random access, and a hash map from each member to its index in the array, for O(1) lookup. Removing uses the swap-with-last trick of the brute force, except that the map tells where the value is, so no scan is needed. The only extra bookkeeping is updating the map entry of the element that moved.

### Algorithm

1. `insert(value)`: if the map contains `value`, return `false`. Otherwise map `value` to the current array length, append it and return `true`.
2. `remove(value)`: look up and delete the map entry of `value`; if absent, return `false`. Pop the last element `last` from the array. If the removed value's index `i` is still inside the array, write `last` into slot `i` and map `last` to `i`. Return `true`.
3. `getRandom()`: return the element at a uniformly random index.

### Correctness

Invariant: the array holds each member exactly once, and the map sends each member to its position in the array. `insert` preserves both by appending and recording the new last index. In `remove`, popping the last element and writing it into the freed slot `i` keeps every member exactly once; the map entry of the removed value is deleted and the entry of `last` is moved to `i`. When `i` was the last index, the pop alone removes the value, and no other entry changes. Because the array holds exactly the members, a uniform index picks each with probability `1/size`.

### Complexity

- Time: O(1) per op — average O(1) hash operations plus O(1) array access, append and pop.
- Space: O(n) — the array and the map each hold one entry per member.

### Trade-offs

Meets the requirement for every operation and is the expected interview answer. It stores each value twice and costs a little more per operation than a plain set; the extra memory is the price of random access. The same "array plus index map" structure is reused for the follow-up with duplicates (map each value to a set of indexes) and for indexed priority queues.

### Pitfalls and edge cases

- Always record the moved element's new index. A stale entry points at a slot that now holds another value or lies past the end of the array, so the next `remove` of the moved value deletes the wrong member or fails.
- When the removed value is itself the last element, do not reinsert it into the map. The references delete the removed value's entry first and only write back when the freed slot is inside the shrunk array.
- `getRandom` on an empty set is excluded by the constraints; real code should guard it.

### Language notes

- Python: `dict.pop(value, None)` reads and deletes in one step; `random.choice(self.values)` draws uniformly.
- TypeScript: a `Map<number, number>` keeps number keys as numbers; check `index === undefined`, since 0 is a valid index.
- Java: `indexOf.remove(value)` returns the boxed index or `null`; compare it with `null`, not with `0`. `values.remove(values.size() - 1)` removes by position (the `remove(int)` overload). `java.util.Random.nextInt(bound)` is uniform over `[0, bound)`.
- Kotlin: `indexOf.remove(value) ?: return false` handles absence in one line; `value in indexOf` checks for a key; `values.random()` draws uniformly.
