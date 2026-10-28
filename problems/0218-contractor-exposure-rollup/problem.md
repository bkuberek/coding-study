# Contractor Exposure Rollup

## Statement

On a construction project, a general contractor hires subcontractors, who hire their own. An insurer wants the total exposure of everyone working under a given contractor, including that contractor.

Each contractor counts once, however many paths lead to it: a crane company hired by two different subcontractors adds its exposure a single time. A contractor with no exposure row contributes `0`, and that includes `root` itself.

A hierarchy that loops back on itself (a contractor that, through its subcontractors, hires itself) is a data error. If a cycle can be reached from `root`, return `-1`. A cycle elsewhere in the input, one that `root` cannot reach, is ignored.

## Input

- `edges`: hiring relations; `edges[i] = [parent, child]` means `parent` hires `child`. The same relation may appear more than once, which changes nothing.
- `contractors`, `exposures`: `exposures[i]` is the exposure of `contractors[i]`
- `root`: the contractor at the top of the rollup

Decimals are shown as quoted strings in the examples, which is how the tests carry them.

## Output

The sum of the exposures of `root` and every distinct contractor reachable from it by following the edges, or `-1` if a cycle is reachable from `root`. Decimals are compared by value, so `175.00` and `175` are the same answer.

## Examples

### Example 1

<!-- case: ex1 -->

`gc` hires `electric` and `plumbing`, and `electric` hires `wiring-co`. The total is 100 + 40 + 30 + 5 = 175.

### Example 2

<!-- case: ex2 -->

`a` hires `b` and `b` hires `a`: a cycle that `a` reaches, so the answer is `-1`. The lists of exposures are empty here, which does not matter because the answer is the cycle marker.

### Example 3

<!-- case: ex3 -->

`crane-co` is hired by both `framing` and `roofing`, but it counts once: 250000.00 + 80000.50 + 42000.25 + 15000.75 = 387001.50. Reaching the same contractor along two paths is not a cycle.

## Constraints

- `0 <= edges.length <= 10^4`
- `0 <= contractors.length == exposures.length <= 10^4`; the names are distinct, 1 to 20 characters of `[a-z0-9-]`.
- `0 <= exposures[i] <= 10^9`, with at most 2 fractional digits.
- The longest path starting at `root` has at most 2000 contractors.

## Follow-ups

- Report the contractors that form the cycle instead of only `-1`.
- Return the exposure per tier (direct subcontractors, their subcontractors, and so on).
- Support a hierarchy that changes over time, so a past rollup can be reproduced (see `versioned-rate-table`).

## Hints

### Hint 1

Build a list of children for every contractor first.

### Hint 2

A single "visited" set cannot tell a shared subcontractor from a loop. Track the contractors on the current path separately from the ones that are already finished.
