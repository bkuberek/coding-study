# Refresh Token Rotation

## Statement

A login service gives each signed-in device a refresh token. Every time the device spends that token it gets a new one, and the old one must never work again. If a spent token shows up a second time, either the device is confused or someone copied the token. The service cannot tell which, so it treats the whole login as compromised and ends it.

There is one honest way to see a spent token twice: the device sent it, the service rotated it, and the reply got lost on the way back. A short grace window keeps that retry from logging the user out.

All the tokens descended from one login form a **family**. A family has one **current** token at a time. Implement `RefreshTokenStore`:

- `RefreshTokenStore(ttlSeconds, graceSeconds)` creates an empty store. A token expires `ttlSeconds` after it was issued, and it stays retryable for `graceSeconds` after it was rotated.
- `issue(familyId, tokenId, now)` starts a family whose current token is `tokenId`. It returns `false`, and changes nothing, when `familyId` or `tokenId` has been issued before, even if that family has since been revoked. Otherwise it returns `true`.
- `rotate(tokenId, newTokenId, now)` handles a presented token. The first of these that applies gives the result:
  1. `"unknown"`: `tokenId` was never issued. Nothing changes.
  2. `"revoked"`: the token's family has been revoked. Nothing changes.
  3. `"expired"`: `tokenId` is the current token and `now >= its issue time + ttlSeconds`. Nothing changes, and the family is not revoked.
  4. `"rotated"`: `tokenId` is the current token. `newTokenId` becomes the current token, issued at `now`, and `tokenId` is spent, at `now`.
  5. `"grace-retry"`: `tokenId` is the token rotated most recently in its family, and `now < the time it was spent + graceSeconds`. Nothing changes: the family keeps its current token.
  6. `"reuse-detected"`: any other spent token. The whole family is revoked.
- `activeToken(familyId, now)` returns the family's current token, or `""` when the family was never issued, has been revoked, or its current token has expired by `now`.

Only `"rotated"` issues `newTokenId`. In every other result the id is forgotten, and presenting it later is `"unknown"`.

Tie-breaks:

- Expiry is checked for the current token only. A spent token is judged by rules 5 and 6 however old it is.
- A token is expired at the exact second `issue time + ttlSeconds`, and the grace window is over at the exact second `spent time + graceSeconds`. With `graceSeconds` of 0, a spent token presented in the same second it was spent is reuse.
- A retry does not reopen the window. It closes at the same second however many retries arrive.
- Calls take effect in the order they are made, including calls with the same `now`.

## Input

- `ttlSeconds`, `graceSeconds`: how long a token lives, and how long a spent token may be retried.
- `familyId`, `tokenId`, `newTokenId`: opaque ids. The caller creates them, and two ids are the same only if they are equal.
- `now`: the current time, in whole seconds. The store never reads a clock.

Each test is a sequence of calls: the constructor first, then the other calls in order.

## Output

One result per call: `null` for the constructor, a boolean for `issue`, and a string for `rotate` and `activeToken`.

## Examples

### Example 1

<!-- case: ex1 -->

`token-a1` is rotated at second 1000, so `token-a2` is current. The same token comes back at second 1010 with a new id. The window of 30 seconds is still open, so this is the lost-reply retry: nothing changes, and `token-a2` stays current. `token-a3`, the id of the retry, was never issued.

### Example 2

<!-- case: ex2 -->

`token-b1` comes back at second 1030, the exact second its window closes. That is reuse, so the family is revoked. Even `token-b2`, the newest token, no longer works, because the service cannot know which of the two holders is the real device.

### Example 3

<!-- case: ex3 -->

The token lives 100 seconds. At second 99 it is still active, and at second 100 it has expired. An expired token is not an attack: the same token is `"expired"` again later, and the family has not been revoked.

## Constraints

- `1 <= ttlSeconds <= 10^7` and `0 <= graceSeconds <= ttlSeconds`, so a token that was just rotated cannot leave its successor expired before the window closes.
- `now` never decreases from one call to the next, and `0 <= now <= 10^12`.
- `newTokenId` is never an id that has been issued.
- Ids are non-empty, at most 40 characters long.
- At most `10^4` calls.

## Follow-ups

- Give a family an absolute lifetime, so that rotating forever does not keep a login alive forever.
- Return the current token from `rotate` on a retry, so a device that lost the reply can recover by itself. What must the store keep for that, and what would it be worth to someone who stole the token?
- In a real store two devices race. Which single atomic step makes `rotate` safe when it runs on several servers at once?
- Store a hash of each token instead of the token. What changes here?

## Hints

### Hint 1

The rules speak of families, not tokens. Find the family first, and let most of the state live there.

### Hint 2

A family needs its current token and when it expires, plus the most recently spent token and when its window closes. Older spent tokens need only to be known.

### Hint 3

Write the checks in the listed order. The order is what makes an old replay into reuse, and not merely a token that expired.
