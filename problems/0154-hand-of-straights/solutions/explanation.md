# Hand of Straights: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n^2) | O(n) | first idea; a correctness baseline |
| sorted-counts | optimal | O(n log n) | O(n) | default answer |
| open-straights | optimal | O(n log n) | O(n) | you want one sweep that never revisits a value |

The whole problem rests on one forced move: the smallest card in the hand cannot sit in the middle or at the end of a straight (nothing smaller exists to precede it), so it must start a straight `v, v + 1, ..., v + k - 1`. Removing that straight leaves a smaller instance of the same problem, so the greedy choice never needs to be undone. A quick necessary condition comes first: the number of cards must be a multiple of `k = groupSize`.

## Approach: brute-force (Repeatedly remove the straight that starts at the smallest card)

### Intuition

Follow the forced move literally. Keep the cards sorted, take the smallest, and remove one card of each of the next `k - 1` values. If any of them is missing, the hand cannot be split.

### Algorithm

1. If the number of cards is not a multiple of `k`, return `false`.
2. Sort the cards.
3. While cards remain: remove the smallest card `v`; for each value from `v + 1` to `v + k - 1`, remove one card with that value, or return `false` if there is none.
4. Return `true`.

### Correctness

Exchange argument: in any valid split, the group containing the smallest card `v` starts at `v` and is exactly `v..v + k - 1`; which copy of each value it uses does not matter, because cards with equal numbers are interchangeable. So if a valid split exists, one exists that contains the straight the algorithm removes, and the rest of the hand must be splittable. If a value is missing, the forced straight cannot be formed and no split exists.

### Complexity

- Time: O(n^2) — up to `n` removals from a list, each a linear search and shift.
- Space: O(n) — the sorted copy of the hand.

### Trade-offs

A direct transcription of the greedy argument, which makes it the oracle. The linear removals are the waste: counting cards per value removes them.

### Pitfalls and edge cases

- With `k = 1` every hand works; the loops do nothing but remove single cards.
- Check the multiple-of-`k` condition first; otherwise the last straight fails only after a lot of work, or a short leftover is mistaken for success.

### Language notes

- Python: `list.remove(value)` deletes the first equal element and raises `ValueError` when none exists.
- TypeScript: `indexOf` plus `splice`; `shift()` removes the smallest card from the front.
- Java: `cards.remove(Integer.valueOf(value))` removes by value; `cards.remove(value)` with an `int` would remove by index, a classic boxing trap.
- Kotlin: `remove(element)` removes by value and `removeAt(index)` by position, so the trap does not exist.

## Approach: sorted-counts (Count the cards and consume straights from the smallest value)

### Intuition

Cards with the same number are interchangeable, so count them per value. Visit the distinct values in increasing order. When a value still has `c` cards left, all of them are now the smallest cards, so each starts its own straight: the next `k - 1` values must each supply `c` cards.

### Algorithm

1. If the number of cards is not a multiple of `k`, return `false`.
2. Count the cards per value.
3. For each distinct value `v` in increasing order with `c = count[v] > 0`: for each `w` from `v` to `v + k - 1`, if `count[w] < c` return `false`, else subtract `c`.
4. Return `true`.

### Correctness

This performs the brute force's removals in bulk: at value `v`, every remaining card with value `v` is a smallest remaining card and must start a straight, by the same exchange argument. Subtracting `c` from the next `k - 1` counts removes exactly those `c` straights. Values below `v` are already at count 0, so no card is ever skipped.

### Complexity

- Time: O(n log n) — sorting the distinct values dominates; the subtractions total O(n), because each straight costs `k` steps and there are `n / k` straights.
- Space: O(n) — the count map.

### Trade-offs

The standard answer: short, and the count map makes the greedy argument easy to state. A sorted map (Java's `TreeMap`) or sorting the keys once gives the order.

### Pitfalls and edge cases

- Skip values whose count has already dropped to 0; they were fully used by earlier straights.
- Read missing values as 0 rather than failing on a lookup.
- `v + k - 1` is at most about `10^9 + 10^4`, which still fits in a 32-bit integer.

### Language notes

- Python: `collections.Counter` returns 0 for missing keys.
- TypeScript: a `Map` plus a numerically sorted key list; the default `sort()` compares as strings and would put 10 before 9.
- Java: `TreeMap` iterates keys in order; updating the value of an existing key while iterating `keySet()` is allowed because it is not a structural change.
- Kotlin: the same `TreeMap`; `merge(card, 1, Int::plus)` counts in one call.

## Approach: open-straights (Sweep the distinct values tracking open straights)

### Intuition

Sweep the distinct values in increasing order and keep track of how many straights are currently open (started but not yet `k` long). Every open straight needs one card of the current value, so the value must exist (no gap) and have at least that many cards; the remaining cards of the value open new straights. A straight opened at the value `k - 1` steps back closes with the current value. A queue of the last `k` opening counts tells how many close at each step.

### Algorithm

1. If the number of cards is not a multiple of `k`, return `false`.
2. Count the cards per value and sweep the distinct values in order, with `open = 0` and an empty queue.
3. At value `v` with count `c`: if `open > 0` and `v` is not the previous value plus 1, return `false`; if `c < open`, return `false`. Push `c - open` (new straights) onto the queue and add it to `open`. If the queue holds `k` entries, pop the oldest and subtract it from `open` (those straights are complete).
4. Return `open == 0`.

### Correctness

Invariant: before value `v`, `open` is the number of straights that must continue through `v`, and the queue holds how many straights started at each of the last values that are still open. The cards at `v` must first extend the open straights (a card at `v` cannot start a straight while a smaller card still needs `v`, by the exchange argument), and the rest start new ones. A gap while straights are open makes them impossible. At the end, every straight must be complete.

### Complexity

- Time: O(n log n) — sorting the distinct values; the sweep itself is O(d) with `d` distinct values.
- Space: O(n) — the count map and a queue of at most `k` entries.

### Trade-offs

Each distinct value is visited exactly once and nothing is decremented ahead of time, which matters when `k` is large and the values are sparse. It needs more bookkeeping than the count-and-consume version; present that one first.

### Pitfalls and edge cases

- Detect gaps only while straights are open; a gap between finished groups is fine.
- With `k = 1`, every new straight closes immediately: the queue reaches size 1 and pops at once.

### Language notes

- Python: `collections.deque` with `popleft`.
- TypeScript: an array with a moving `head` index acts as a queue without O(n) `shift` calls.
- Java and Kotlin: `ArrayDeque<Integer>` / `ArrayDeque<Int>`; iterating `TreeMap` entries yields values in order with their counts.
