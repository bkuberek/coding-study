# Debug: Pagination Query Strings

## Statement

An API reads its paging parameters from the query string, such as `page=2&perPage=10`. `pageWindow` works out which rows to fetch, and returns three numbers: `[offset, limit, nextPage]`.

- `page` is counted from 1, and defaults to 1.
- `perPage` defaults to 20, and is capped at `maxPerPageSetting`, which comes from the service's environment.
- `offset` is how many rows come before this page, `(page - 1) * limit`, and `limit` is the page size after the cap.
- `nextPage` is `page + 1` when rows remain after this page, and `0` when none do.
- A parameter that is missing or empty (`page=`) takes its default.

The code type-checks, and the first page of every list works. Find the bugs and fix them.

### Bug report

> **Title:** Page 2 says there is nothing after it, and page size 9 returns 50 rows
>
> A client walking a 45-row list gets `nextPage: 0` on page 2, and sees it stop early. One client asking for `perPage=9` gets 50 rows, while another asking for `perPage=100` gets 100, though the limit in the environment is `MAX_PER_PAGE=50`. A support engineer also saw a `nextPage` of 21 once, on a request for page 2 of a long list. Nobody has reported a problem with the defaults.

## Input

- `queryString`: the query string as a client sent it, without the `?`
- `maxPerPageSetting`: the value of the environment variable, digits only
- `totalItems`: how many rows the list has

## Output

`[offset, limit, nextPage]`, three whole numbers.

## Examples

### Example 1

<!-- case: ex1 -->

No parameters: the defaults, and 40 rows remain after the first 20. This case passes as shipped.

### Example 2

<!-- case: ex2 -->

The first page of ten: rows remain, so the next page is 2. This case passes as shipped too.

## Constraints

- `0 <= totalItems <= 10^6`
- A value in `queryString` that is present and not empty is digits forming a whole number of at least 1. `maxPerPageSetting` is one too.
- Other parameters may appear, and are ignored.

## Follow-ups

- This statement promises that values are digits. A real client doesn't. Where would you refuse `page=abc`, and what does `Number("abc")` give you if you don't?
- `process.env.MAX_PER_PAGE` is a string too. Where in a service do you turn configuration into numbers, so that this can't happen twice?

## Hints

### Hint 1

Call it with `page=2&perPage=10` and a total of 45, and work out by hand what each line produced. Add `typeof` to your logging.

### Hint 2

The type of `query` is `Record<string, any>`, and `any` turns every check off. What is the real type of each value, and what is the real type of its default?

### Hint 3

In JavaScript, `"2" + 1`, `"2" - 1`, `10 + "10"` and `"9" > "50"` each follow a different rule. Try all four in a Node prompt.

### Hint 4

`??` only replaces `null` and `undefined`. What does an empty query value look like?
