# Debug: Falsy Plan Update: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| nullish-checks | optimal | O(n) | O(n) | default answer: `??` for defaults, and an explicit check for presence |

Here `n` is the length of the request body.

## Approach: nullish-checks (Ask whether a value is present, not whether it is truthy)

### Intuition

`x || fallback` asks "is `x` truthy?", and this code wants to ask "is `x` present?". Those two questions disagree on exactly the values that matter most in a plan: `0`, `""` and `false`.

- `priceCents || 1900` turns a free plan into a paid one.
- `trialDays || 14` gives a trial to a plan that has none.
- `label || "Standard"` undoes clearing a label.
- `active || true` is `true` for every possible input, which makes the field a constant.
- `if (body.capCents)` skips a cap of zero, the one cap that freezes billing.

`??` asks the right question: it falls back only for `null` and `undefined`. The `if` needs the same question, written out.

### Say it out loud

"`||` treats every falsy value as missing: 0, the empty string, false and NaN along with null and undefined. For a default I want `??`, which only replaces null and undefined. And `if (amount)` skips zero, so I check for presence explicitly: `amount != null` or the long form. Zero and empty are values someone chose."

### Debugging approach

1. **Reproduce with the values in the report.** `{"priceCents":0}` gives 1900.
2. **List what's falsy.** `false`, `0`, `-0`, `0n`, `""`, `null`, `undefined` and `NaN`. Check each of these against what the field can legitimately hold.
3. **Read every `||` and every bare `if` on a value** in the function: each one is the same question.
4. **Check the half-fixes.** `??` on the fields leaves the `if` (`h6`). `!== undefined` everywhere lets `null` through, and `Math.min(1900, null)` is 0 (`h7`). `body.active === true` makes a missing `active` false (`ex2`).

### Algorithm

1. Parse the body, and give it a type.
2. For each field, use `??` with its default.
3. If `capCents` is present, take the smaller of it and the price.
4. Format the summary line.

### Correctness

`a ?? b` is `b` exactly when `a` is `null` or `undefined`, which is the statement's definition of a missing field, so every other value passes through unchanged. The cap applies exactly when `capCents` is neither `null` nor `undefined`, and `Math.min` of two numbers is the smaller one, so a cap of 0 gives a price of 0, and a cap above the price leaves it alone.

### Complexity

- Time: O(n) — parsing the body is linear in its length, and everything else is a fixed number of steps.
- Space: O(n) — the parsed body.

### Trade-offs

`body.capCents != null` is the short form of the presence check: `!=` with `null` is the one loose equality many style guides allow, because it covers `undefined` too, and it reads as one idea. The long form used here avoids the lint exception. Destructuring defaults, `const { priceCents = 1900 } = body`, apply only for `undefined`, so a `null` would get through: a third meaning of "missing".

### Pitfalls and edge cases

- The general trap: `||` for defaults, and a bare `if (value)` for presence. Both are fine for objects, and wrong for numbers, strings and booleans.
- `||` is still right when you do want to treat an empty value as missing, as with `?page=` in a query string, where `""` means "not given". Decide per field.
- `x || true` is always truthy. If `x` could ever be `false`, this line is a bug by construction.
- `Math.min(1900, null)` is 0, because `null` converts to 0, and `Math.min(1900, undefined)` is `NaN`.
- `0`, `""` and `false` do show up in JSON. `NaN` and `undefined` never do, since JSON has no way to write them.

### Prevention

- The lint rules `prefer-nullish-coalescing` and `strict-boolean-expressions` flag exactly these lines.
- Give the parsed body a type. `JSON.parse` returns `any`, which is why the compiler says nothing. With `priceCents?: number | null`, the strict-boolean lint has what it needs.
- In tests, include `0`, `""` and `false` for every field that can hold them. "Normal values" pass any version of this code.

### Language notes

TypeScript accepts `any || 1900` happily, and its type system doesn't know "falsy" as a concept. `??` can't be mixed with `||` or `&&` without parentheses, which is a syntax error by design.
