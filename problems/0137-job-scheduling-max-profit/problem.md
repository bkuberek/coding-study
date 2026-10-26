# Job Scheduling for Maximum Profit

## Statement

A contractor is offered `n` jobs. Job `i` occupies the time from `startTime[i]` up to `endTime[i]` and pays `profit[i]`. The contractor can work on only one job at a time, so the chosen jobs must not overlap. A job that ends at time `t` does not overlap a job that starts at time `t`: one can follow the other immediately.

Return the largest total profit of a set of jobs in which no two overlap.

Reference: this is our own wording of LeetCode problem 1235, [Maximum Profit in Job Scheduling](https://leetcode.com/problems/maximum-profit-in-job-scheduling/).

## Input

- `startTime`: the start time of each job
- `endTime`: the end time of each job
- `profit`: the payment for each job

The three arrays have the same length, and position `i` of each describes job `i`. The jobs are in no particular order.

## Output

The maximum total profit over all sets of pairwise non-overlapping jobs.

## Examples

### Example 1

<!-- case: ex1 -->

Take the jobs [1, 3), [4, 6) and [6, 9) for 20 + 70 + 60 = 150. The last two touch at time 6, which is allowed. The job [2, 5) overlaps both [1, 3) and [4, 6), so it does not fit.

### Example 2

<!-- case: ex2 -->

All three jobs start at time 1, so they overlap pairwise and only one can be taken: the best pays 6.

### Example 3

<!-- case: ex3 -->

The first job ends at time 5 exactly when the second starts, so both can be done, for 3 + 4 = 7.

## Constraints

- `1 <= startTime.length == endTime.length == profit.length <= 2000`
- `1 <= startTime[i] < endTime[i] <= 10^9`
- `1 <= profit[i] <= 10^4`

## Follow-ups

- Picking the most profitable job first, or the job that ends first, can both fail. Find small counterexamples.
- Once the jobs are sorted, which earlier job does a chosen job leave room for, and how fast can you find it?
- How does this compare with House Robber, where the "conflict" is simply the neighboring element?

## Hints

### Hint 1

Sort the jobs by end time. For the jobs up to position `i`, either job `i` is not used, or it is used together with the best schedule of the jobs that end no later than job `i` starts.

### Hint 2

Let `best[i]` be the most profit from the first `i` jobs in end-time order. Then `best[i] = max(best[i - 1], profit + best[p])`, where `p` counts the jobs whose end time is at most the start of job `i`.

### Hint 3

The end times are sorted, so `p` can be found by binary search instead of a linear scan.
