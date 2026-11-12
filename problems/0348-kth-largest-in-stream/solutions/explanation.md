# Kth Largest in a Stream: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| sorted-list | brute | O(n) per add | O(n) | the stream is short, or as the obviously correct baseline |
| min-heap | optimal | O(log k) per add | O(k) | default answer; `k` is much smaller than the stream |

The tracker has to answer one question after each new number: what is the `k`-th largest of everything seen so far? Here `n` is the number of scores recorded. Keeping all of them in order answers the question at once but pays to keep the order. The key observation behind the heap is that scores below the cutoff never matter again, because once `k` scores are higher, a score can never be the `k`-th largest of a collection that only grows.

## Approach: sorted-list (Keep every number in a sorted list)

### Intuition

Store all numbers in ascending order. The `k`-th largest is then the `k`-th entry counted from the end of the list. To add a number, find its place with a binary search and insert it there, so the list stays sorted.

### Algorithm

1. In the constructor, sort `nums` into a list.
2. In `add(value)`: find the position where `value` belongs, insert it there, and return the entry `k` places from the end of the list.

### Correctness

The list is sorted before the first `add` and after each insertion, because each value goes at a position where everything to its left is no larger and everything to its right is no smaller. In a sorted ascending list of `m` entries, the entry at position `m - k` (counting from 0) has exactly `k - 1` entries after it, and equal values count separately, which matches the definition of the `k`-th largest. The first `add` leaves at least `k` entries, so the position exists.

### Complexity

- Time: O(n) per add — the binary search is O(log n), but opening a slot in the middle of an array-backed list moves every entry after it, which is O(n) in the worst case; building the list from `nums` once costs O(n log n).
- Space: O(n) — every number is kept.

### Trade-offs

The simplest code and an ideal check for the heap version. It is slow for long streams because it keeps and shifts numbers that can no longer be the answer. A balanced tree or a skip list would make each insertion logarithmic, but they hold all `n` numbers; the heap is simpler still and holds only `k`.

### Pitfalls and edge cases

- Count `k` from the end: `values[-k]` in Python is the `k`-th largest, while `values[k]` is a small number near the start.
- Insert duplicates; do not skip a value that is already present, or the ties would be miscounted.
- The starting list may be empty, so the constructor must work with no numbers.

### Language notes

- Python: `bisect.insort` finds the position and inserts; the `bisect` documentation notes that the O(log n) search is dominated by the O(n) insertion step. A negative index such as `values[-self.k]` counts from the end.
- TypeScript: `Array.prototype.sort` needs a numeric comparison `(a, b) => a - b`, because without one it compares the values as text. `splice(position, 0, value)` inserts in place.
- Java: `Collections.binarySearch` returns `-(insertion point) - 1` when the value is absent, so the code converts it back; `ArrayList.add(index, element)` shifts the elements after that position to the right, per its documentation.
- Kotlin: `nums.sorted()` returns a new sorted list, which the `ArrayList` constructor copies; `binarySearch` on a list has the same negative-result convention as Java's.
- Go: `slices.BinarySearch` returns the position where the value is or would be, and `slices.Insert` shifts `s[i:]` up to make room, which is the linear step.
- Rust: `partition_point` returns the first position whose entry is not smaller than `value`, and `Vec::insert` takes time proportional to the length because it shifts every entry after the position.

## Approach: min-heap (Min-heap holding only the k largest)

### Intuition

You only ever report the `k`-th largest, and a number that has `k` larger numbers above it can never be reported again. So hold on to just the `k` largest numbers seen so far, in a container that hands you the smallest of them at once. That smallest member is the `k`-th largest overall, and it is exactly the answer. A min-heap is such a container: the smallest item is always at the top, and inserting or removing the top takes logarithmic time in the heap's size. When a new number arrives, push it in; if the heap now holds `k + 1` numbers, the smallest of them cannot be among the `k` largest, so remove it.

### Algorithm

1. Create an empty min-heap.
2. To offer a number: push it onto the heap; if the heap now has more than `k` entries, remove the smallest.
3. In the constructor, offer every number of `nums`.
4. In `add(value)`: offer `value` and return the smallest number in the heap, the top.

### Correctness

The heap always holds the `k` largest numbers recorded so far, or all of them when fewer than `k` exist. This holds at the start (nothing recorded, nothing held) and survives each offer: after the push, the heap holds the previous `k` largest plus the new number; the removed smallest of those `k + 1` numbers has `k` numbers at least as large, so it is not among the `k` largest of the new collection, while the `k` that stay are. When at least `k` numbers have been recorded, the heap holds exactly `k`, and the smallest of the `k` largest is the `k`-th largest, with ties counting separately because duplicates are kept as separate entries.

### Complexity

- Time: O(log k) per add — one push and at most one removal on a heap that never holds more than `k + 1` entries, and reading the top is constant. Offering the starting list costs O(m log k) for `m` numbers.
- Space: O(k) — the heap never keeps more than `k` numbers, however long the stream is.

### Trade-offs

Much faster than the sorted list on long streams, and the memory depends on `k` rather than on the length of the stream, which matters when the stream is endless. Its limit is the rank it can answer: it knows only the top `k`, so a change of `k` needs a new tracker. When `k` is close to the stream length the two approaches do about the same work. The one-shot version of this question, over an array you already have, is the kth largest element problem.

### Pitfalls and edge cases

- Use a min-heap, not a max-heap. With a max-heap on top you can see the largest number, but the cutoff is the smallest of the top `k`.
- Keep the heap at `k` entries: forgetting to remove the smallest after a push makes the top the smallest number ever seen, and `add` returns a wrong value.
- The constructor must apply the same rule to `nums` as `add` applies to new numbers, including the case where `nums` is longer than `k` and the case where it holds exactly `k - 1` numbers.
- A new number equal to the current top does not need special care: pushing it and removing a smallest entry leaves an equal value in the heap.

### Language notes

- Python: `heapq` works on a plain list and is a min-heap: according to the documentation, `heap[0]` is the smallest item. `heappush` adds a number; `heapreplace` pops the smallest and pushes the new number in one step, which the documentation says is more efficient than `heappop` followed by `heappush` and can be more appropriate for a fixed-size heap. The reference uses it once the heap is full and only for a number larger than the top.
- TypeScript: the reference writes a small `MinHeap` class over an array, with `push` (sift up) and `replaceTop` (sift down), because it needs no library for it; the children of index `i` are `2i + 1` and `2i + 2`.
- Java: `PriorityQueue` orders by natural ordering and its head is the least element; `offer` and `poll` are O(log n) and `peek` is constant time, per the documentation. Iterating over a `PriorityQueue` does not give sorted order, so read only the head.
- Kotlin: there is no heap in the Kotlin standard library for the JVM target, so the reference uses `java.util.PriorityQueue` directly, with the same behavior as in Java; `peek()` returns a platform type, which is safe here because the heap is full when `add` reads it.
- Go: `container/heap` is a min-heap over any type that implements `heap.Interface` (`Len`, `Less`, `Swap`, `Push` and `Pop`); the reference defines `intHeap` as a slice of ints, and `top[0]` is the minimum. `heap.Push` and `heap.Pop` are O(log n) in the heap's size.
- Rust: `BinaryHeap` is a max-heap, so the reference stores `Reverse(number)`, which makes `pop` and `peek` return the smallest. `pop` takes O(log n) and `peek` takes constant time; `peek` returns an `Option`, and `expect` states that the heap is full when `add` reads it.
