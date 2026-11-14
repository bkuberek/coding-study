# Debug: Window Shrink

## Statement

A sales report has one number per day. The dashboard looks for the best streak: `k` consecutive days whose numbers are all different, with the largest total. Given `nums` and `k`, the function `maxDistinctWindowSum` you start from should return the largest sum of any `k` consecutive elements whose values are all different, or `0` when no such window exists.

The code keeps a running sum and a count per value as the window slides. It passes some tests and fails others. Find the bug and fix it, keeping the single pass.

### Bug report

> **Title:** "Best streak" is too low on most reports, and too high on one
>
> Analysts compared the dashboard with a spreadsheet that checks every window by brute force. On most reports the dashboard's best streak is lower than the spreadsheet's. It seems to find only streaks near the start of the period, and with `k = 1` it reports the first day's value instead of the best day's. One report goes the other way: the dashboard shows a higher total than any valid streak, as if it had accepted a window with a repeated value. Reports with very few distinct values look right.

## Input

- `nums`: the values in order
- `k`: the window length

## Output

The maximum sum over all windows `nums[i..i+k-1]` whose `k` values are pairwise distinct, or `0` if there is none.

## Examples

### Example 1

<!-- case: ex1 -->

The window `[9, 8, 7]` has distinct values and sum 24; the other windows sum to 16 and 10. This case passes as shipped, because the best window is the first one.

### Example 2

<!-- case: ex2 -->

The valid windows are `[1, 5, 4]` (10), `[5, 4, 2]` (11) and `[4, 2, 9]` (15); the last two windows repeat 9. The answer is 15. The shipped code returns 10.

## Constraints

- `1 <= k <= nums.length <= 10^5`
- `1 <= nums[i] <= 10^4`

## Follow-ups

- Return the starting index of the best window instead of its sum.
- Find the longest window with at most `k` distinct values. Which line of the fixed code becomes the shrink condition?

## Hints

### Hint 1

Reproduce with `k = 1` on `[3, 7, 2]`. Every single element is a valid window, so the answer is 7. What does the code return, and after which step does it stop finding windows?

### Hint 2

Print `counts` at every step. What is the size of the map compared with the number of different values actually inside the window?

### Hint 3

The code uses the number of keys in `counts` as the number of distinct values in the window. When does a key stop belonging to the window?

### Hint 4

Find the report that came out too high: a window of length `k` with a repeated value, at a moment when one key with count `0` is still in the map.
