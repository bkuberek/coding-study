# Container With Most Water

## Statement

A row of vertical bars stands on flat ground, one unit apart. Bar `i` has height `height[i]`. Pick two bars as the walls of a container; the ground between them is its floor. Water poured in rises until it would spill over the shorter wall, so the container holds `(j - i) * min(height[i], height[j])` units of water for walls at positions `i < j`. The bars between the walls do not matter: treat them as if they were not there.

Return the largest amount of water any pair of walls can hold.

Reference: this is our own wording of LeetCode problem 11, [Container With Most Water](https://leetcode.com/problems/container-with-most-water/).

## Input

- `height`: the height of each bar, from left to right

## Output

The maximum of `(j - i) * min(height[i], height[j])` over all positions `i < j`.

## Examples

### Example 1

<!-- case: ex1 -->

The walls at positions 1 and 5 have heights 7 and 8. They are 4 units apart and the water stops at height 7, so they hold 4 * 7 = 28. The outermost pair is wider, but its right wall has height 1, so it holds only 6 * 1 = 6.

### Example 2

<!-- case: ex2 -->

The two middle bars hold 1 * 9 = 9. The outer bars are three times as far apart, but at height 2 they hold only 6.

## Constraints

- `2 <= height.length <= 10^5`
- `0 <= height[i] <= 10^4`

## Follow-ups

- Measuring every pair is quadratic. Can you find the answer in one pass?
- Why is it safe to discard the shorter of the two outer walls, but not the taller one?
- How does this differ from Trapping Rain Water, where the bars in between do hold water back?

## Hints

### Hint 1

Start with the widest container, the two outermost bars. Any other container is narrower, so it can only win by being taller.

### Hint 2

Compare the two walls. If you keep the shorter wall and move the other one inward, the water level cannot rise above the shorter wall while the width shrinks.

### Hint 3

So the shorter wall has already been paired with every partner that could beat the current best. Drop it, move that side inward, and repeat until the walls meet.
