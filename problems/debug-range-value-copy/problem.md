# Debug: Range Value Copy

## Statement

A loyalty program closes its books at the end of every month. Member `i` starts the month with `opening[i]` points. Each entry `[member, points]` of `earnings` adds `points` to that member. At the close, a balance above `limit` is cut down to `limit`, and the points above it expire.

The function `closeMonth` you start from should return one statement line per member, in member order: `[balance, expired]`, the balance carried into the next month and the number of points that expired. A member at or below the limit has `0` expired points.

The code passes some tests and fails others. Find out why and fix it.

### Bug report

> **Title:** Points above the cap never expire
>
> Finance noticed that the program's liability keeps growing. Some members hold more than twice the 50,000-point cap, and every month-end statement shows 0 expired points, for everyone. Statements of members below the cap are correct. Two reviewers read the cap check and agreed that the comparison and both assignments are right.

## Input

- `opening`: each member's balance at the start of the month
- `earnings`: pairs `[member, points]`, one per purchase that earned points
- `limit`: the largest balance a member may carry into the next month

## Output

One `[balance, expired]` pair per member, in member order.

## Examples

### Example 1

<!-- case: ex1 -->

Member 0 earns 50 and 25 points (175 in total) and member 1 earns 300 (2800). Both stay below the cap of 5000, so nothing expires. This case passes as shipped.

### Example 2

<!-- case: ex2 -->

Member 0 sits exactly at the cap, which is allowed, and member 1 ends one point below it. This case passes too.

## Constraints

- `1 <= opening.length <= 1000`
- `0 <= opening[i] <= 10^6`
- `0 <= earnings.length <= 10^4`
- `earnings[j] = [member, points]` with `0 <= member < opening.length` and `1 <= points <= 10^5`
- `0 <= limit <= 10^9`

## Follow-ups

- Change `accounts` to `[]*account`. Does the original cap loop work then? What does that change cost?
- Go 1.22 changed `for` loop variables. Did that change affect this bug? Why not?

## Hints

### Hint 1

Print `accounts` right after the cap loop. Then print `acct` inside the loop, after the two assignments.

### Hint 2

In `for _, acct := range accounts`, what is `acct`: the element, or something else?

### Hint 3

The earnings loop updates `accounts[member]` and works. What does it do differently from the cap loop?

### Hint 4

Range over the indexes and update `accounts[i]`, or take a pointer `acct := &accounts[i]`.
