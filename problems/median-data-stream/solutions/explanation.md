# Median of a Data Stream: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| sorted-array | brute | O(n) addNum, O(1) findMedian | O(n) | few additions, many queries |
| two-heaps | optimal | O(log n) addNum, O(1) findMedian | O(n) | default answer |

`n` is the number of values added so far. Both approaches keep every value, because any of them can become the median later; they differ in how much order they maintain.

## Approach: sorted-array (Keep a sorted array and binary-insert each number)

### Intuition

If the values are kept sorted, the median is just the middle element or the average of the two middle elements. A binary search finds where a new value belongs.

### Algorithm

1. `addNum(num)`: binary-search the first position whose value is at least `num` and insert `num` there.
2. `findMedian()`: with `m = size / 2`, return `values[m]` for an odd size, or `(values[m - 1] + values[m]) / 2` for an even size.

### Correctness

Invariant: the array holds every value added so far, in ascending order. Inserting at the binary-searched position keeps it sorted. For a sorted array of odd size the middle index `m` holds the median, and for an even size the two middle values sit at `m - 1` and `m`, so `findMedian` follows the definition.

### Complexity

- Time: O(n) addNum, O(1) findMedian — the search is O(log n), but opening a slot shifts up to n elements. Over a sequence of n calls that is O(n^2), worst on a descending stream, where every insertion goes to the front.
- Space: O(n) — the array.

### Trade-offs

Simple and exact, which makes it the oracle, and faster in practice than its bound suggests: the shift is a single block move (`memmove` or `System.arraycopy`), so its constant factor is tiny. The quadratic growth still shows as the stream gets longer, and a heap does strictly less work. If queries for other percentiles were needed, the sorted array (or a balanced tree) would be the better structure.

### Pitfalls and edge cases

- Integer division of the middle sum: `(a + b) / 2` truncates in Java and Kotlin unless one operand is a `double` (`2.0`).
- Return a floating-point value for an odd count too; the comparator accepts `42.0` for `42`, but the declared return type is `double`.

### Language notes

- Python: `bisect.insort` does the search and the insertion in one call, and `/` is true division.
- TypeScript: no library binary search; `(low + high) >>> 1` halves the range without floating point, and `splice(index, 0, value)` inserts.
- Java: `Collections.binarySearch` returns `-(insertion point) - 1` for a missing value; `ArrayList.add(index, value)` shifts with `System.arraycopy`.
- Kotlin: `MutableList.binarySearch` uses the same negative encoding; `toDouble()` converts the odd-count median.
- Go: `slices.BinarySearch` returns the insertion position directly (plus a found flag), and `slices.Insert` shifts the tail to open the slot, which is the O(n) step. `float64(a+b) / 2` adds the two middle integers first, so the division is floating point and the sum stays exact.
- Rust: `partition_point(|&value| value < num)` is the lower bound on the sorted `Vec`, and `Vec::insert` shifts the tail. `f64::from(a + b) / 2.0` adds in `i32` (at most 2 * 10^5 here) and converts before dividing.

## Approach: two-heaps (Max-heap of the lower half, min-heap of the upper half)

### Intuition

Split the values into a lower half and an upper half. The median depends only on the largest value of the lower half and the smallest value of the upper half, and a max-heap and a min-heap give exactly those in O(1). Keep the halves balanced (the lower half may hold one extra value) and ordered (everything low is at most everything high).

### Algorithm

1. `addNum(num)`:
   1. Push `num` into `low` (the max-heap), then move `low`'s largest value into `high` (the min-heap).
   2. If `high` now holds more values than `low`, move `high`'s smallest value back into `low`.
2. `findMedian()`: if `low` holds more values, return its top; otherwise return the average of both tops.

### Correctness

Invariants after every `addNum`: (a) every value in `low` is at most every value in `high`, and (b) `low` holds as many values as `high` or one more.

Step 1.1 moves `m`, the largest of `low`'s values and `num`, into `high`. Every value left in `low` is at most `m`, because `m` was the largest. It is also at most every older value of `high`: the older values of `low` satisfied (a) already, and if `num` stayed in `low`, then `m` was an older value of `low`, so `num <= m <= min(high)`. Hence (a) holds after step 1.1. Step 1.2 moves the smallest value of `high` into `low`, which keeps (a), and it restores (b): step 1.1 grew `high` by one, so `high` is larger than `low` exactly when the two were equal before the call.

With (a) and (b), the sorted order of all values is `low` followed by `high`, and the middle value is `low`'s top (odd count) or the middle pair is the two tops (even count).

### Complexity

- Time: O(log n) addNum, O(1) findMedian — at most three heap operations per addition; reading the tops is constant.
- Space: O(n) — both heaps together hold every value.

### Trade-offs

The standard answer: logarithmic insertion with constant-time queries, and a classic example of maintaining an invariant across two structures. It cannot remove arbitrary values or answer other percentiles; for a sliding-window median you would need lazy deletion or an ordered multiset instead. For bounded value ranges (the follow-up), counting buckets with a running position give O(1) additions.

### Pitfalls and edge cases

- Inserting directly into one heap based on a comparison with the median works too, but it is easy to get the empty-heap cases wrong; routing through `low` first removes them.
- The balance rule must be the same in `addNum` and `findMedian`: here `low` is the one that may be larger.
- Sum the two tops in a type that cannot overflow; with values up to 10^5 an `int` sum is safe, but the habit matters for wider ranges.

### Language notes

- Python: `heapq` has only a min-heap, so `low` stores negated values; `heappushpop` pushes and pops in one sift, which is exactly step 1.1.
- TypeScript: no built-in priority queue, so the reference writes one `Heap` class parameterized by a `before` comparison and instantiates it twice, as a max-heap and as a min-heap.
- Java: `new PriorityQueue<>(Comparator.reverseOrder())` is the max-heap; `(low.peek() + high.peek()) / 2.0` unboxes both tops and divides as `double`.
- Kotlin: `PriorityQueue<Int>(reverseOrder())` and the default `PriorityQueue<Int>()`; `peek()` returns a platform type, so the arithmetic compiles without null checks because both heaps are non-empty whenever they are read.
- Go: `container/heap` is a min-heap over any type implementing `heap.Interface`, so the reference declares one `intHeap` and stores the lower half negated, as the Python version does, which makes the same type the max-heap. There is no push-and-pop in one call, so the routing step is `heap.Push` on `low` followed by `heap.Pop` from it, then a push onto `high`; it is still O(log n).
- Rust: `BinaryHeap<i32>` is the max-heap for the lower half and `BinaryHeap<Reverse<i32>>` is the min-heap for the upper half, so nothing is negated. `BinaryHeap` has no push-and-pop either, so routing is `push` then `pop`. `peek()` returns an `Option`; both halves are known to be non-empty when read, so `expect` states that.
