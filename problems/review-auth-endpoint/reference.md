# Review: Login Endpoint: Reference

Verdict: request changes; this must not ship as is. One injection gives a full authentication bypass, and every login writes the user's plaintext password to a log readable by dozens of people at a third party. A strong review separates what an attacker can exploit today (blockers) from hardening, explains the exploit concretely enough that nobody argues severity, and offers a migration path for the password hashes instead of only saying "use bcrypt".

## Blocker

- `login.py:30-34` `login`: the email is concatenated into the SQL string. This is SQL injection, and here it is a full authentication bypass: an email of `x' UNION SELECT 1, '<sha256 of "s" + "pw">', 's', true --` makes the query return a row with an attacker-chosen hash and salt, so the password `pw` "matches" and the attacker gets a session as user 1 (or any id). Use a parameter: `cursor.execute("SELECT ... WHERE email = %s", (body.email.lower(),))`. Grep the rest of the port for the same pattern.
- `login.py:27`: `body.model_dump()` logs the plaintext password of every login attempt, including attempts with a mistyped password for another site. The logs go to a third party for 90 days and are readable by every engineer and support agent. Never log the request body of an authentication endpoint; log the outcome, a user id when known, and a request id. Treat the logs written by any deployment of this code as a credential exposure: purge them and consider forced resets.

## Major

- `login.py:50`: logs the session token; anyone who can read logs can hijack any session. Log the user id and a token fingerprint at most.
- `login.py:56` `require_service_key`: compares the shared secret with `!=`, which can return as soon as the first byte differs; an attacker who can reach the endpoint can in principle recover the key from response times. Use `hmac.compare_digest(x_service_key.encode(), settings.internal_service_key.encode())`. Also ask why an internal endpoint is on the public router at all; serving it only on the internal network removes the exposure.
- `login.py:21-22` `hash_password`: salted SHA-256 is a fast hash; a leaked `users` table can be brute-forced at billions of guesses per second on a GPU. Keep verifying legacy hashes, but rehash on successful login with a slow, memory-hard function (argon2id, or bcrypt or scrypt) and store the algorithm with the hash, so the table migrates as users log in. For users who never log in again, wrap the old hash (`argon2id(sha256(salt + password))`) in a batch job. The security team asked for this explicitly; porting the weak scheme into new code makes it harder to remove later.
- `login.py:26` `login`: no rate limiting or throttling on a public endpoint that was just the target of credential stuffing. Limit attempts per account and per IP (with backoff rather than hard lockout, which becomes a denial-of-service tool), consider a challenge after repeated failures, and check passwords against known-breached lists. Link the platform's rate limiter if one exists.
- `login.py:39`: `is_active` is read and never checked, so deactivated or banned accounts can still log in. Reject them with the same generic error as a wrong password.
- `login.py:51`: `set_cookie("session", token)` without `httponly=True`, `secure=True` and `samesite="lax"` (or `"strict"`): any XSS can read the session, the cookie is sent over plain HTTP, and cross-site requests carry it. Also set an expiry.
- Sessions never expire: there is no `expires_at` in the insert and nothing checks age. Add absolute and idle timeouts.

## Minor

- `login.py:36-41`: different responses for an unknown email (404, "No account with this email") and a wrong password (401, "Wrong password") let anyone enumerate registered emails, which makes credential stuffing cheaper. Return the same 401 and message for both. The unknown-email path also returns faster because it skips hashing; hash a dummy password on that path so timing does not leak it either.
- `login.py:44-47`: the session token is stored in plaintext; anyone with read access to the database (or a backup) can use every live session. Store a SHA-256 of the token and look sessions up by that.
- `login.py:63` `revoke_sessions`: also concatenates SQL. It is not exploitable today only because FastAPI validates `user_id` as an `int`; use a parameter anyway so a later type change does not open a hole.
- `test_login.py`: tests cover only the happy path and a wrong password, and `test_login_rejects_wrong_password` asserts the enumerating message. Add tests for an injection payload in the email, an inactive user, an unknown email (same response as a wrong password), cookie flags, and that the password never appears in captured logs (`caplog`).
- `login.py:32`: the email is lowercased in the query but not necessarily in stored data migrated from the monolith; normalize consistently (or compare with `lower(email)` and an index on it). Ask how the monolith stored emails.

## Nit

- `login.py:26`: no response model; declare one so the OpenAPI schema documents the response.
- `login.py:29`: the cursor is never closed; use `with conn.cursor() as cursor:`.
- `test_login.py:9`: the test salt is named `pepper`, which means something else in password storage; call it `salt`.
- `login.py:55`: `Header(...)` as a default is the older FastAPI style; `Annotated[str, Header()]` is the current one.
