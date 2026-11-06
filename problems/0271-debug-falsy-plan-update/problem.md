# Debug: Falsy Plan Update

## Statement

A billing admin tool saves a subscription plan from a JSON body. `applyPlanUpdate` fills in the defaults, applies an optional price cap, and returns a one-line summary:

```text
price=<priceCents> trial=<trialDays> label=<label> seats=<seats> active=<active>
```

| Field | Default |
|-------|---------|
| `priceCents` | 1900 |
| `trialDays` | 14 |
| `label` | `Standard` |
| `seats` | 5 |
| `active` | `true` |

A field that is missing or `null` takes its default. Any other value is what the admin asked for, and it is used as it is.

`capCents` is optional too. When it is missing or `null`, there is no cap. Otherwise the price is the smaller of `priceCents` and `capCents`.

The amounts are invented. The tool works for every plan the team tried. Find the bugs and fix them.

### Bug report

> **Title:** We can't make a plan free, or turn one off
>
> Support set a plan's price to 0 for a promotion and it saved as 1900. Setting the trial to 0 days gives 14. Clearing the label brings back `Standard`. Deactivating a plan does nothing at all: it stays active. And a cap of 0, which we use to freeze billing during an outage, is ignored. Normal values have always worked.

## Input

- `bodyJson`: the request body, a JSON object, whose fields, when present, have the types in the table

## Output

The summary line. `label` is written as it is, an empty one included, and `active` as `true` or `false`.

## Examples

### Example 1

<!-- case: ex1 -->

Every field is set, to a value that counts as true in JavaScript, and the cap of 2500 lowers the price. This case passes as shipped.

### Example 2

<!-- case: ex2 -->

An empty body takes every default. This case passes as shipped too.

## Constraints

- `0 <= priceCents, capCents, trialDays, seats <= 10^8`
- `label` is at most 40 printable ASCII characters.
- `bodyJson` is valid JSON, and its fields have the types above or are `null`.

## Follow-ups

- This function gets `null` and "missing" to mean the same thing. In a `PATCH`, they usually can't. How would this code differ?
- Which lint rule would have flagged these lines, and why does the compiler stay quiet?

## Hints

### Hint 1

Write down every value `||` treats as false. There are more than `null` and `undefined`.

### Hint 2

`x || fallback` asks "is `x` truthy?". What does this function actually need to ask?

### Hint 3

There's an `if` here too. What happens when the value it tests is 0?

### Hint 4

Look at `active` on its own: for which inputs can `body.active || true` be anything other than `true`?
