# Debug: Pagination Query Strings: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| numbers-at-the-edge | optimal | O(1) | O(1) | default answer: turn text into numbers once, where it enters, and do arithmetic only on numbers |

## Approach: numbers-at-the-edge (Convert to numbers at the edge)

### Intuition

Every value from a query string or an environment variable is a string. The code never converts them, and each operator then treats a string in its own way:

- `(page - 1) * perPage` works, because `-` and `*` have only a numeric meaning, so they convert. This is why the offset is always right, and why the bug survives a casual read.
- `offset + perPage` joins text when `perPage` is a string: `10 + "10"` is `"1010"`, and `"1010" < 45` then converts back to compare, so page 2 of 45 rows says nothing remains. On page 1 it is `0 + "10"`, `"010"`, which converts to 10, so the first page always works.
- `page + 1` joins too: `"2" + 1` is `"21"`, which `Number` then dresses up as 21.
- `perPage > maxPerPageSetting` compares two strings, character by character: `"9" > "50"` is true, and `"100" > "50"` is false. When `perPage` takes its numeric default, the same line compares numbers, so the defaults are fine.
- `Number(perPage)` at the end hides all of this: the return value has the right type, whatever happened on the way.

`any` is what lets it compile. `URLSearchParams` would have typed these as `string`, and the compiler would have refused `page - 1`.

### Say it out loud

"Query values and environment variables are strings, so `+` concatenates and `>` compares lexicographically, while `-` and `*` coerce. The code happens to work for the defaults because those are real numbers. I'd parse once at the boundary, give the rest of the function numbers, and remove the `any`, which is what stopped the compiler from telling me."

### Debugging approach

1. **Reproduce the report.** `page=2&perPage=10` with 45 rows gives `[10, 10, 0]`, when 3 is the next page.
2. **Log types, not just values.** `typeof page` is `string` when the query has it, and `number` when it takes the default. A value with two possible types is the bug's shape.
3. **Evaluate each operator by hand.** Each of the three symptoms is one operator: `+` joining, `+` joining again, and `>` on two strings.
4. **Check the half-fixes.** Fixing `page + 1` alone leaves `offset + perPage` (`h1`). Converting at the end leaves the compare (`h3`, `h4`). Converting with `Number(query.page ?? 1)` leaves the empty value, since `Number("")` is 0 (`h10`).

### Algorithm

1. Read `page` and `perPage` as text. A missing or empty value takes the default, and anything else becomes a number.
2. Take the smaller of `perPage` and the setting, converted to a number, as `limit`.
3. Work out `offset` and `nextPage` on those numbers.

### Correctness

Once the values are converted, every operator means what it reads as. `Math.min` caps by numeric value whatever the digit counts. `offset + limit` is the number of rows up to the end of this page, so `nextPage` is non-zero exactly when rows remain. The default path and the query path share every line after the conversion, so a test of one covers the other.

### Complexity

- Time: O(1) — a fixed number of operations, given a query string of bounded length.
- Space: O(1) — a few numbers.

### Trade-offs

`Number` against `parseInt`: `parseInt("12abc")` is 12 and `parseInt("1e3")` is 1, while `Number("12abc")` is `NaN` and `Number("1e3")` is 1000. Neither is validation. A real endpoint checks `/^\d+$/` first and refuses the request, which this problem's constraints rule out to keep the focus on the conversions. A schema library does the whole job at the edge, and is what most services would use.

### Pitfalls and edge cases

- The general trap: `+` is the one arithmetic operator that prefers strings. If either side is a string, it concatenates.
- Relational operators compare text only when both sides are strings. `"9" > 50` converts and is false; `"9" > "50"` doesn't and is true. So a default that is a number hides the bug until a client sends the parameter.
- `query.x ?? default` gives you the empty string for `?x=`, and `Number("")` is 0, not `NaN`. Here that would make `page` 0 and the offset negative.
- Defaults of a different type from the parsed value are a smell: `query.page ?? 1` has the type `string | number` in spirit, whatever `any` says.
- Destructuring defaults have the same problem: `const { page = 1 } = query`.
- `Number(x)` at a return statement satisfies the types while hiding that `x` was a string all along.

### Prevention

- Ban `any` at the boundary: the rule `no-explicit-any` would have flagged the `Record<string, any>`, and without it the compiler refuses this code.
- Parse input and configuration in one module, and hand the rest of the code a typed object.
- Test with a query parameter present, not only absent, and with values of different digit counts: 9, 10 and 100.

### Language notes

Web frameworks often type query values loosely, which is exactly how this `any` usually arrives. `process.env` values are always strings or `undefined`. Node's `URLSearchParams.get` returns `string | null`, which the reference uses so that the compiler checks the conversion.
