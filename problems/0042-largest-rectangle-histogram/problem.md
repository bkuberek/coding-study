# Largest Rectangle in Histogram

## Statement

A histogram is a row of bars of width 1 standing side by side with no gaps; bar `i` has height `heights[i]`. Draw an axis-aligned rectangle that lies entirely inside the bars: it covers a contiguous range of bars, starts at the ground, and is no taller than the lowest bar in its range.

Return the largest area such a rectangle can have.

Reference: this is our own wording of LeetCode problem 84, [Largest Rectangle in Histogram](https://leetcode.com/problems/largest-rectangle-in-histogram/).

## Input

- `heights`: the height of each bar, from left to right

## Output

The largest area of a rectangle that fits inside the histogram.

## Examples

### Example 1

<!-- case: ex1 -->

Bars 2 to 4 (heights 5, 4 and 5) hold a rectangle of height 4 and width 3, area 12. Widening it to include bar 1 drops the height to 2 (area 10), and the full width only allows height 1 (area 7).

### Example 2

<!-- case: ex2 -->

The bar of height 0 splits the histogram in two. On the right, three bars of height 3 give area 9, which beats the two bars of height 4 on the left (area 8).

## Constraints

- `1 <= heights.length <= 10^5`
- `0 <= heights[i] <= 10^4`

## Follow-ups

- Trying every pair of end bars costs O(n^2). For a fixed bar used as the rectangle's height, how far can the rectangle extend?
- Can you find, for every bar, the nearest lower bar on each side in one pass?
- How does this solve the largest rectangle of ones in a binary matrix?

## Hints

### Hint 1

Some bar in the best rectangle is its lowest bar. If bar `i` is the lowest, the rectangle stretches from just after the nearest lower bar on the left to just before the nearest lower bar on the right.

### Hint 2

Keep a stack of bar indexes with increasing heights. When a lower bar arrives, the bars it pops have just found their right boundary.

### Hint 3

When a bar is popped, the bar now below it on the stack is its left boundary, so its width is `current - below - 1`. A final bar of height 0 flushes the stack.
