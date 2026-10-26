# Review: Login Endpoint: Rubric

## Finding the issues

- [ ] Flags the SQL injection in the login query and explains that it allows logging in as another user, not just reading data.
- [ ] Flags the plaintext password logged by `model_dump()`.
- [ ] Flags the session token in logs.
- [ ] Flags the non-constant-time comparison of the service key and names `hmac.compare_digest`.
- [ ] Flags the fast SHA-256 password hash.
- [ ] Flags the missing rate limiting on login.
- [ ] Flags that `is_active` is never checked.
- [ ] Flags the missing cookie flags and the missing session expiry.
- [ ] Flags user enumeration through different responses (and timing) for unknown emails.
- [ ] Notices the second concatenated query and judges correctly that it is not exploitable today.

## Prioritization

- [ ] Marks the injection and the password logging as blockers and says the change must not ship.
- [ ] Recognizes that logs already written are a credential exposure that needs cleanup, not just a code fix.
- [ ] Keeps style comments as nits and does not let them dilute the security findings.

## Actionable comments

- [ ] Shows the parameterized query.
- [ ] Proposes a migration path for legacy hashes (verify old, rehash on login, wrap the rest) instead of a rewrite that locks users out.
- [ ] Lists the missing tests concretely (injection payload, inactive user, unknown email, cookie flags, no password in logs).

## Tone and collaboration

- [ ] Describes exploits factually, without alarmism or blame, and credits the use of `secrets.token_urlsafe`.
- [ ] Offers to pair or links existing helpers (rate limiter, logging filters) where they exist.

## Asking about intent

- [ ] Asks why the internal revoke endpoint is on the public router.
- [ ] Asks how the monolith stored and normalized emails before relying on `lower()`.
