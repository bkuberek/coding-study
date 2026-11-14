# Token Claim Validator: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| ordered-checks | optimal | O(c + s) | O(c) | default answer |

`c` is the total number of names and values in the rows, and `s` the number of required scopes.

## Approach: ordered-checks (Index the claims and run the rules in their stated order)

### Intuition

A signature tells you who wrote a token. Every bug in this problem comes from treating that as if it also said "and it is meant for you, right now". The rules form a funnel: can these claims be read at all, who wrote them, who are they for, are they valid now, and finally what do they allow. Each stage only makes sense once the stage before it has passed, which is why the order is part of the contract.

### Algorithm

1. Walk the rows into a lookup from name to values. A name you have already seen is `malformed-claim`.
2. Check the shape: exactly one value for `iss`, `exp` and `nbf`, at least one for `aud`, and only ASCII digits in `exp` and `nbf`.
3. Return `missing-claim` when `iss`, `aud` or `exp` has no row.
4. Compare `iss` and each value of `aud` for exact equality.
5. Parse the two timestamps, which step 2 made safe, and apply the two time rules with the skew.
6. Turn the values of `scope` into a set, and require every entry of `requiredScopes` to be in it.

### Correctness

The function returns at the first failing rule and tests the rules in the stated order, so the reason is always the first failure. Steps 2 and 3 pass only when `iss`, `aud` and `exp` exist with the right number of values, so the later steps never read a value that is absent. A token that reaches `"ok"` has passed every rule, since each rule's failure condition has been tested and found false.

### Complexity

- Time: O(c + s) — one pass over the rows, one pass over `aud` and `scope`, and one set lookup per required scope.
- Space: O(c) — the lookup and the set of granted scopes hold the values of the rows.

### Trade-offs

Returning at the first failure tells a caller as little as possible, which is what you want at the edge: a stranger should not learn that a token was almost good. Collecting every failure is better for a server-side log, and it costs only a list. A scan of the rows for each rule needs no lookup and is fast enough for 50 rows, but it misses duplicates unless you add a separate check, and duplicates are the point of rule 1.

### Pitfalls and edge cases

- **A missing `exp` is not a token that never expires.** Code that only checks `exp` when it is present accepts a token the issuer never meant to live forever (`h6`).
- **`0` is a value.** A truthiness test treats `exp` of `"0"` as absent, so a token from 1970 passes (`h9`), and an `nbf` of `"0"` must not count as missing either (`h10`).
- **Duplicate claims.** A lookup keeps one of two `iss` rows, and a different parser elsewhere may keep the other. Whichever one wins, the token means two things, so it is refused (`h11`, `h12`).
- **Number parsers are generous.** `parseInt` reads `1790000600abc` as a number (`h13`). `Number` accepts exponents and surrounding spaces (`h14`, `h15`). Python's `int` accepts spaces and the digits of other scripts, and `isdigit` agrees with it (`h16`). A regular expression ending in `$` accepts a trailing newline in Python unless you use `fullmatch` (`h17`).
- **The two time rules are not mirrors.** A token is dead at the exact second `exp + skew` (`h1`, `h3`), and it is alive at the exact second `now + skew == nbf` (`h4`, `h5`). RFC 7519 defines `exp` and `nbf` with the same asymmetry. Skew always forgives, on both sides: subtracting it from `exp` rejects a good token (`h2`).
- **Matching by prefix or substring.** `https://login.example.attacker.test` starts with the trusted issuer (`h19`), `orders-api` is inside `orders-api-internal` (`ex3`, `h23`), and `orders:read` is inside `orders:read-all` (`h27`). Everything here is exact, including case and a trailing slash (`h18`, `h20`).
- **`aud` is a list.** The expected audience may be any of its values, not only the first (`ex1`, `h21`), and an empty row is malformed (`h22`).
- **Required scopes are all of them.** Holding one of two is not enough (`h25`). No `scope` row is fine when nothing is required (`h26`), and refused when something is (`h24`).
- **Priority.** A token can fail several rules at once, and the order decides which one you report (`ex2`, `h28` to `h32`).
- **Names are case-sensitive.** `EXP` is an unknown claim, so `exp` is missing (`h33`).

### Language notes

- Python: `name, *values = row` splits a row. `re.fullmatch` is the one that is strict about the whole text. Integers do not overflow, so the sum with the skew needs no care.
- TypeScript: `const [name, ...values] = row` splits a row. A non-global `RegExp`'s `$` does not match before a trailing newline, and `[0-9]` is the honest spelling of ASCII digits. At most 15 digits keeps `Number` exact, since every integer up to 2^53 is representable.
