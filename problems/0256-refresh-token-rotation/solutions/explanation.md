# Refresh Token Rotation: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| family-records | optimal | O(1) per call | O(t) | default answer |

`t` is the number of tokens issued.

## Approach: family-records (One record per family and a lookup from token to family)

### Intuition

Rotation turns a stolen token from a long-lived key into a tripwire. A thief and the real device now hold tokens from the same chain, and sooner or later one of them presents a token the other has already spent. The store cannot tell which of the two did it, so the only safe response is to end the whole chain. That is why the state belongs to the family, and why the newest token dies along with the old ones.

The grace window is a deliberate hole in that tripwire, there to absorb a lost reply. It is one token wide and a few seconds long, because every second it stays open is a second in which a thief can use a stolen token without tripping anything.

### Algorithm

1. Keep a lookup from family id to its record, and from every token ever issued to the same record. The record holds the current token and when it expires, the most recently spent token and when its window closes, and whether the family is revoked.
2. `issue`: refuse a known family or token id. Otherwise create the record.
3. `rotate`: find the record through the token, then test in the stated order: unknown, revoked, current and expired, current, retry inside the window, and otherwise reuse.
4. Rotating moves the current token to `lastSpent`, sets the window from `now`, and registers the new token with a fresh expiry from `now`.
5. `activeToken`: return the current token unless the family is unknown or revoked, or the token has expired.

### Correctness

A token that was ever issued stays in the token lookup, so a spent token always finds its family, and only ids that were never issued are `"unknown"`. A record has one current token, and only `"rotated"` changes it, so a family can never have two live tokens. Only the most recently spent token matches rule 5, and its window was fixed when it was spent, since a retry writes nothing, so a retry cannot extend it. Everything else that is known and not current is spent, and it reaches rule 6, which revokes through the shared record, so the revocation reaches every token of the family and no other family.

### Complexity

- Time: O(1) per call — each call does a fixed number of map lookups and field writes.
- Space: O(t) — one lookup entry per token ever issued, and one record per family.

### Trade-offs

Keeping every spent token forever is what makes an old replay detectable, and it is also what grows without bound. A real store deletes a family's tokens once the family can no longer be used: after its last token expires, plus however long you still want a replay to raise an alarm.

The grace window trades detection for availability. With no window, one lost reply logs a user out. With a long one, a thief who steals a token just as it is spent can use it unnoticed. A few seconds is the usual answer. Some designs bind the retry to the same device, so that a window can stay open without helping a thief.

Revoking on any reuse also means that a buggy client which replays a token logs its own user out. That is the right failure: it is noisy, and it is safe.

### Pitfalls and edge cases

- **Revoking only the presented token.** The thief may hold the newest one. The whole family ends, the newest token with it (`ex2`, `h3`, `h11`).
- **Letting a grace retry mint a token.** That creates two live tokens in one family. A retry changes nothing, and its `newTokenId` is forgotten (`h5`).
- **A window that any spent token can use.** Only the most recently spent token gets it. Once `token-a2` is spent too, `token-a1` is reuse, even inside its own window (`h3`, `h4`).
- **A retry that reopens the window.** Writing the time on every retry lets a stream of retries keep the hole open forever (`h6`).
- **Checking expiry first.** A long-gone token that comes back is reuse, not merely expired, and treating it as expired hides the replay you most want to see (`h7`).
- **Revoking on expiry.** An expired current token is ordinary: a device that was offline for a week should have to log in again, not raise an alarm (`ex3`, `h8`).
- **Expiry from the family's first token.** Each token lives `ttlSeconds` from its own issue (`h9`).
- **Off by one at both edges.** A token dies at the exact second of its expiry (`ex3`, `h18`), and the window closes at the exact second it ends (`ex2`, `h1`). With no window, the same second is already reuse (`h2`).
- **`revoked` versus `reuse-detected`.** After the alarm, tokens report `"revoked"`, even the one that tripped it. Alarms should fire once per incident (`h11`).
- **Revoking across families.** Another login of the same user is not touched (`h10`).
- **Registering `newTokenId` too early.** It only exists after `"rotated"` (`h5`, `h12`).
- **`issue` over old state.** A revoked family's id does not come back (`h13`), and family ids and token ids are different namespaces (`h17`).

### Language notes

- Python: a small `dataclass` holds the record, and both lookups point at the same instance, so setting `revoked` is seen from every token.
- TypeScript: a plain object behind an interface does the same, shared by reference between the two `Map`s. A `Map` is the honest choice for ids that arrive from outside: a plain object would treat a token called `__proto__` as something it already has.
