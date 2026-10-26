# Last Stone Weight: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| sort-each-round | brute | O(n^2 log n) | O(n) | the literal simulation; tiny piles |
| sorted-insert | intermediate | O(n log n + n W) | O(n) | no heap available; moderate piles |
| max-heap | optimal | O(n log n) | O(n) | default answer |

`n` is the number of stones and `W` the heaviest weight (at most 1000 here). Every smash removes at least one stone, so there are at most `n - 1` rounds. The approaches differ only in how they find the two heaviest stones and put the leftover back.

## Approach: sort-each-round (Sort the stones before every smash)

### Intuition

Simulate the rules literally: sort the pile, take the two heaviest from the end, and put the leftover (if any) back on the pile. Repeat.

### Algorithm

1. Copy the weights into a list.
2. While at least two stones remain:
   1. Sort the list.
   2. Remove the last two values `y` (heaviest) and `x`.
   3. If `x != y`, append `y - x`.
3. Return the remaining weight, or 0 if the list is empty.

### Correctness

After sorting, the last two values are the two heaviest stones, which is exactly the pair the rules smash. Steps 2.2 and 2.3 apply the rule for that pair, so each iteration performs one round of the game. The loop stops when fewer than two stones remain, as the rules require.

### Complexity

- Time: O(n^2 log n) — up to `n - 1` rounds, each sorting up to n values.
- Space: O(n) — the copy of the pile.

### Trade-offs

Obviously faithful to the statement, which makes it the oracle, but it re-sorts a pile that is already almost sorted after the first round. TimSort (Python, Java's object sort) notices sorted runs and is close to linear here, so in practice it behaves like O(n^2); it is still far slower than a heap at 10^4 stones.

### Pitfalls and edge cases

- A pile that empties completely must return 0, not raise on an empty list.
- In TypeScript, `sort()` without a comparator sorts numbers as strings (`1000` before `2`).

### Language notes

- Java: `Arrays.sort(remaining, 0, size)` sorts only the live prefix of a primitive array, so no list or boxing is needed; the live size shrinks as stones are destroyed.
- Kotlin: `removeAt(lastIndex)` removes the last element; `firstOrNull() ?: 0` covers the empty pile.

## Approach: sorted-insert (Keep the stones sorted and binary-insert each new stone)

### Intuition

Sort once. The two heaviest stones are then always at the end, and the only thing that disturbs the order is the leftover stone of a smash. Put it back at its sorted position with a binary search instead of re-sorting everything.

### Algorithm

1. Sort the weights ascending.
2. While at least two stones remain:
   1. Remove the last two values `y` and `x`.
   2. If `x != y`, binary-search the insertion point of `y - x` and insert it there.
3. Return the remaining weight, or 0.

### Correctness

Invariant: the list is sorted ascending at the start of every round. Removing from the end keeps it sorted, and inserting at the binary-searched position keeps it sorted. With the invariant, the last two values are the two heaviest stones, so each round applies the rules correctly.

### Complexity

- Time: O(n log n + n W) — the first sort costs O(n log n), and a round costs O(1) unless it leaves a stone behind, when it does an O(log n) search and shifts up to n elements to open the slot. A round leaves a stone only when the heaviest stone is unique, and the leftover is lighter than it, so the heaviest weight drops with every such round: at most `W` rounds shift. That is O(n^2) when every weight is distinct, which needs n <= W; with weights of at most 1000 and up to 10^4 stones, the shifts grow linearly in n.
- Space: O(n) — the sorted list.

### Trade-offs

A useful middle step when no priority queue is at hand, and fast in practice because the shift is a single memory move (`memmove` in Python's `insort`, `System.arraycopy` in `ArrayList.add`). Without the bound on the weights it is quadratic, which a heap avoids.

### Pitfalls and edge cases

- Inserting at the wrong side of equal values does not matter here, but the search must return a position within `[0, size]`.
- Java's and Kotlin's `binarySearch` return `-(insertion point) - 1` for a missing value; forgetting to decode it inserts at a negative index.

### Language notes

- Python: `bisect.insort` does the binary search and the insertion in one call.
- TypeScript: there is no library binary search, so the reference writes `lowerBound`; `(low + high) >>> 1` halves without floating point. `splice(index, 0, value)` inserts.
- Java: `Collections.binarySearch` on an `ArrayList<Integer>`; `remove(size() - 1)` resolves to the index overload because the argument is an `int`.
- Kotlin: `MutableList.binarySearch(value)` from the standard library, with the same negative encoding.

## Approach: max-heap (Max-heap of the stone weights)

### Intuition

The game only ever needs the largest element and inserts new elements: the exact interface of a priority queue. A max-heap gives the heaviest stone in O(1), removes it in O(log n) and inserts in O(log n), with no shifting.

### Algorithm

1. Build a max-heap of all weights.
2. While the heap holds at least two stones:
   1. Pop `y`, then pop `x`.
   2. If `x != y`, push `y - x`.
3. Return the top of the heap, or 0 if it is empty.

### Correctness

The heap holds exactly the stones in the pile. Popping twice yields the two heaviest stones in order, and pushing the leftover keeps the heap equal to the pile after the smash. Each iteration is one round of the game, so the heap's final content is the game's final pile.

### Complexity

- Time: O(n log n) — building the heap is O(n); each of at most `n - 1` rounds does at most three O(log n) heap operations.
- Space: O(n) — the heap.

### Trade-offs

The standard answer and the reason this problem sits in the heap pattern. With weights limited to 1000, a counting approach over weight buckets is also possible, but its bookkeeping is error-prone and its worst case depends on the weight range rather than on n.

### Pitfalls and edge cases

- Popping from an empty heap when one stone is left: the loop condition must be "at least two".
- Python's `heapq` is a min-heap: forgetting to negate gives the lightest stones instead of the heaviest.

### Language notes

- Python: `heapq` only provides a min-heap, so the reference stores negated weights; `heapify` builds the heap in O(n). The leftover pushed back is `second - heaviest`, which is the negation of `heaviest - second`.
- TypeScript: no built-in priority queue, so the reference implements a binary max-heap with a bottom-up heapify in the constructor.
- Java: `new PriorityQueue<>(capacity, Comparator.reverseOrder())` turns the default min-heap into a max-heap; the initial capacity must be at least 1. `poll` unboxes into `int`.
- Kotlin: the same `java.util.PriorityQueue` with `reverseOrder()`; `heap.peek() ?: 0` covers the empty heap because `peek` returns null there.
