# Debug: Nil Map Write

## Statement

An analytics service counts page views. The `PageViews` type you start from should support:

- `NewPageViews()`: an empty counter.
- `Record(page, visitor)`: count one view of `page` by `visitor`.
- `Views(page)`: the number of views of `page`.
- `UniqueVisitors(page)`: the number of different visitors who viewed `page`.
- `Merge(source, target)`: `source` moved to the address `target`. Every view of `source` now counts as a view of `target`, by the same visitor, and `source` has no views afterwards. Merging a page into itself changes nothing.

A page that has no views, because it was never recorded or because it was merged away, reports `0` for both queries.

The code passes the unit tests that came with it. It fails in production. Find out why and fix it.

### Bug report

> **Title:** Analytics worker crashes after a page is moved
>
> Marketing moved `/pricing` to the new address `/plans`, and the nightly job that calls `Merge("/pricing", "/plans")` crashed the analytics worker. The stack trace ends in `Merge`. Last month the same job merged `/faq` into `/help`, two pages that both had traffic, without trouble. Queries for pages nobody has visited return zero and have never crashed.

## Input

- `page`, `source`, `target`: page addresses
- `visitor`: an opaque visitor id

## Output

`Views` and `UniqueVisitors` return counts; `Record` and `Merge` return nothing.

## Examples

### Example 1

<!-- case: ex1 -->

`ana` viewed `/home` twice and `ben` once: 3 views by 2 visitors. Nobody viewed `/blog`, so both queries return 0. This case passes as shipped.

### Example 2

<!-- case: ex2 -->

`/pricing` has 2 views (`ana`, `ben`) and `/plans` 1 view (`ana`). After the merge `/plans` has 3 views by 2 visitors, since `ana` counts once, and `/pricing` has none. This case passes too.

## Constraints

- At most 1000 operations per test.
- Page addresses and visitor ids are 1 to 30 printable ASCII characters.

## Follow-ups

- `Views` sums over every visitor of a page. How would you make it O(1) without slowing `Record` down?
- Which operations on a nil map are safe, and which panic? Where else in Go does a zero value behave like an empty collection for reading but not for writing?

## Hints

### Hint 1

Run a test where the target of `Merge` has never been recorded. Then run one where it has.

### Hint 2

What does `p.visits[target]` return when `target` is not a key? Print it with `%#v` and compare it with `nil`.

### Hint 3

`Views` and `UniqueVisitors` also look up pages that may be missing, and they never crash. What do they do with the result that `Merge` does not?

### Hint 4

The fix is in the write path: create the inner map, and store it in `p.visits`, before writing to it. `Record` already does this.
