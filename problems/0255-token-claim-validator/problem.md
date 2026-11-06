# Token Claim Validator

## Statement

An orders service accepts signed access tokens. An earlier step has already checked the signature and decoded the payload, so there is no cryptography here. A good signature only proves who wrote the token, though. It does not prove that this service should accept the token at this moment, and that is your job.

`validateClaims` checks the decoded claims against what this service expects and returns `"ok"`, or the reason for the first rule that fails. The rules run in this order, and the first failure decides the result:

1. `malformed-claim`: the claims cannot be trusted to mean one thing. Any of these is malformed:
   - Two rows have the same claim name, whichever claim it is.
   - `iss`, `exp` or `nbf` does not have exactly one value, or `aud` has no value.
   - The value of `exp` or `nbf` is anything but one or more of the digits `0` to `9`.
2. `missing-claim`: there is no `iss`, `aud` or `exp` row. Claim names are case-sensitive. `nbf` and `scope` are optional.
3. `wrong-issuer`: the value of `iss` is not exactly `expectedIssuer`.
4. `wrong-audience`: no value of `aud` is exactly `expectedAudience`.
5. `expired`: `now >= exp + clockSkewSeconds`.
6. `not-yet-valid`: there is an `nbf`, and `now + clockSkewSeconds < nbf`.
7. `insufficient-scope`: some entry of `requiredScopes` is not exactly one of the values of `scope`. A token without a `scope` row has no scopes.

Any other claim, such as `sub` or `jti`, is ignored beyond the duplicate check in rule 1.

## Input

- `claims`: the decoded payload, one row per claim: the claim's name, then its values. `["aud", "orders-api", "billing-api"]` is a claim `aud` with two values. Numbers are written as text, exactly as they were decoded.
- `now`: the current time, in whole seconds since the epoch. The function never reads a clock.
- `clockSkewSeconds`: how far this service's clock may disagree with the issuer's.
- `expectedIssuer`, `expectedAudience`: who must have written the token, and who it must be for.
- `requiredScopes`: every scope this request needs.

## Output

`"ok"`, or the one reason named by the first failed rule.

## Examples

### Example 1

<!-- case: ex1 -->

The token expired 30 seconds ago, which is inside the 60 seconds of skew. The audience this service expects is the second of two, and that is fine. `sub` is ignored, and the only required scope is present.

### Example 2

<!-- case: ex2 -->

The token has expired, and it also lacks the required scope. Expiry is checked first, so the reason is `expired`.

### Example 3

<!-- case: ex3 -->

`orders-api-internal` contains the expected audience but is not equal to it. This token was written for another service.

## Constraints

- `0 <= claims.length <= 50`, and every row has at least the claim's name.
- A row has at most 50 values, each of them at most 200 characters long.
- A value of `exp` or `nbf` made only of digits has at most 15 of them, so it fits a `long`.
- `0 <= now <= 10^12` and `0 <= clockSkewSeconds <= 3600`.
- `0 <= requiredScopes.length <= 50`.

## Follow-ups

- Require `iat`, the time the token was issued, and refuse one from the future, or one older than a maximum age.
- Accept any issuer from a configured list, with an expected audience per issuer.
- Return every failed rule at once. Why might a service log the full list but still send the caller only one reason?

## Hints

### Hint 1

Turn the rows into a lookup first, and watch for a name you have already seen.

### Hint 2

Write the numeric check yourself. Most library number parsers accept more than digits.

### Hint 3

The two time rules are not mirror images. Check what happens at the exact second on each side of each one.
