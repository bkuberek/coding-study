# Debug: Unsigned Underflow

## Statement

A deployment dashboard answers the question "which release was live at time `at`?". `release_times` holds the times of a service's releases, in milliseconds, strictly increasing. The release live at `at` is the last one whose time is at or before `at`. The function `latest_release` you start from should return its index, or `-1` when `at` is earlier than every release, including when the service has no releases.

The code is a binary search ported line by line from the team's Java service, where it has worked for years. The Rust version passes many tests and fails others. Find out why and fix it.

### Bug report

> **Title:** Dashboard crashes for queries before the first release
>
> Since the Rust rewrite, the dashboard crashes when an auditor asks what was live before a service's first release, and when it opens a service that has never released. In development builds the log says `attempt to subtract with overflow`. In the production build, which turns overflow checks off, the same requests fail with `index out of bounds: the len is 3 but the index is 9223372036854775807`. Queries at or after the first release work, as they did in Java.

## Input

- `release_times`: release times in milliseconds, strictly increasing
- `at`: the time of the query, in milliseconds

## Output

The index of the last release with a time at or before `at`, or `-1`.

## Examples

### Example 1

<!-- case: ex1 -->

The release at 2000 is the last one at or before 2500. This case passes as shipped.

### Example 2

<!-- case: ex2 -->

A release is live from its own time on, so at 3000 the release at index 2 is live. This case passes too.

## Constraints

- `0 <= release_times.length <= 10^5`
- `0 <= release_times[i] <= 2^53 - 1`, strictly increasing
- `0 <= at <= 2^53 - 1`

## Follow-ups

- The standard library has a method that does this search for you. Which one, and what does it return?
- The Java version computed `mid = (lo + hi) / 2`. Could that overflow in Java? In Rust?

## Hints

### Hint 1

Run a case where `at` is before the first release. Which line does the panic point at?

### Hint 2

What type do `lo`, `hi` and `mid` have? What is `0 - 1` in that type?

### Hint 3

In Java, `hi` becomes `-1` and the loop condition `lo <= hi` ends the loop. Which value would `hi` need to hold for the same idea to work in Rust?

### Hint 4

Search the half-open range `[lo, hi)` instead: start with `hi = release_times.len()`, set `hi = mid` when `mid` is too late, and loop while `lo < hi`. No bound is ever decremented.
