# Jump Game

## Statement

You stand on index 0 of the array `nums`. From index `i` you may jump forward to any index from `i + 1` up to `i + nums[i]`, so `nums[i]` is the longest jump allowed from there, and a value of 0 means you cannot move on from that index. Decide whether you can reach the last index.

Reference: this is our own wording of LeetCode problem 55, [Jump Game](https://leetcode.com/problems/jump-game/).

## Input

- `nums`: the maximum jump length at each index

## Output

`true` if some sequence of jumps from index 0 lands on the last index, otherwise `false`.

## Examples

### Example 1

<!-- case: ex1 -->

Jump from index 0 to index 1 (one step), then from index 1, whose value is 3, straight to the last index 4.

### Example 2

<!-- case: ex2 -->

Indexes 0, 1 and 2 can only reach as far as index 3, whose value is 0, so index 4 is out of reach.

## Constraints

- `1 <= nums.length <= 10^4`
- `0 <= nums[i] <= 10^5`

## Follow-ups

- Marking every index each reachable index can jump to is O(n^2) in the worst case. What single number summarizes everything you have learned so far?
- Can you solve it by walking backwards from the last index instead?
- How would you find the smallest number of jumps when the last index is reachable?

## Hints

### Hint 1

If you can reach index `i`, you can also reach every index before it. So the reachable indexes always form a prefix of the array.

### Hint 2

Walk forward keeping the farthest index reachable so far. If the current index is beyond it, you are stuck.

### Hint 3

From the other side: the last index is a goal. Any index that can jump to the current goal becomes the new goal.
