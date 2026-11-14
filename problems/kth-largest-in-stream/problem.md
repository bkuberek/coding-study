# Kth Largest in a Stream

## Statement

A baking contest awards prizes to the `k` highest scores, and the judges' scores arrive one at a time. After every new score, the display board must show the prize cutoff: the lowest score that is still among the top `k`. That is the `k`-th largest score so far, counting from 1, where the highest score is the 1st largest.

Equal scores count separately. If the scores so far are `22, 22, 15` and `k` is 2, the 1st largest is 22, the 2nd largest is the other 22, and the 3rd largest is 15. The cutoff is therefore 22.

Implement the class `KthLargestTracker`:

- `KthLargestTracker(k, nums)` starts a tracker for the `k`-th largest. `nums` holds the scores that already exist; it can be empty and in any order.
- `add(value)` records one new score and returns the `k`-th largest of all scores recorded so far, those in `nums` included.

You may assume that when `add` returns, at least `k` scores have been recorded, so the answer always exists.

Reference: this is our own wording of LeetCode problem 703, [Kth Largest Element in a Stream](https://leetcode.com/problems/kth-largest-element-in-a-stream/).

The tracker will be fed far more scores than `k`. Sorting everything after each new score is simple, but the board has to keep up, and a data structure called a heap lets you do much better. A min-heap is a container with two cheap operations: it tells you the smallest item it holds immediately, and it lets you insert an item or remove the smallest item in time proportional to the logarithm of its size, rather than to its size.

## Input

- Constructor: `k`, the rank to report (1 means the highest score), and `nums`, the scores recorded before the tracker starts.
- `add(value)`: the next score.

Each test is a sequence of calls: the constructor first, then the methods in order.

## Output

- `add` returns the current `k`-th largest score, as an integer.
- The constructor returns nothing.

The expected output of a test lists one result per call, with `null` for the constructor.

## Examples

### Example 1

<!-- case: ex1 -->

With `k = 2` and the starting scores 15, 7 and 22, the two highest are 22 and 15. Adding 9 changes nothing at the top, and the 2nd largest stays 15. Adding 30 makes the top two 30 and 22, so the cutoff rises to 22. Adding 22 gives a second 22 that counts on its own, so the top two are 30 and 22 and the answer is still 22. Adding 5 changes nothing. Adding 25 pushes a 22 out of the top two, leaving 30 and 25, so the cutoff is 25.

### Example 2

<!-- case: ex2 -->

With `k = 1` the tracker reports the highest score so far, and the starting list may be empty. After -4 the highest is -4; -9 is lower, so the answer stays -4; then 0 becomes the highest, and a second 0 keeps it there.

## Constraints

- `1 <= k <= 10^5`
- `0 <= nums.length <= 10^5`, and `nums.length >= k - 1`, so the first `add` always leaves at least `k` scores.
- `-10^4 <= nums[i], value <= 10^4`
- At most `10^5` calls to `add`.

## Follow-ups

- Which scores does your tracker never look at again after they fall below the cutoff? Does it need to keep them?
- When a new score is lower than the current cutoff, how much work should `add` do?
- What would you change to report the `k`-th smallest instead?

## Hints

### Hint 1

Think about what the board needs. It does not need to know the whole ranking, only the single score at place `k`. Which scores can never be the answer again once `k` higher scores exist?

### Hint 2

Suppose you remembered only the `k` highest scores seen so far. Where among them is the cutoff? And what kind of container would give you that score immediately, without searching?

### Hint 3

A min-heap of at most `k` numbers does exactly that: its smallest item sits at the top, and you can insert and remove in logarithmic time. Once the heap holds `k` scores, a new score smaller than the top cannot be among the `k` highest, so it can be ignored, and a larger one replaces the top. Before that, every score simply goes in.

### Hint 4

Offer every starting score to the heap using the same rule as for new scores: push it, and if the heap now holds more than `k` scores, remove the smallest. Then `add` offers the new score the same way and returns the top of the heap. Check which way round your language's heap works: Python's `heapq` and Java's `PriorityQueue` put the smallest item first, while Rust's `BinaryHeap` puts the largest first and needs `std::cmp::Reverse` to flip it.
