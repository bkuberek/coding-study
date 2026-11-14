# OAuth Client with PKCE (TypeScript): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | per request | per session | default answer: check the state before the code, the signature before the claims, keep the provider's keys until a token names one you lack, and keep only the newest refresh token |

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | The code flow with PKCE, `state` and `nonce` | `src/pkce.ts`, the random values and the S256 challenge. `login` keeps an attempt behind a `login` cookie; `callback` takes it once, checks the state, exchanges the code in `src/provider.ts`, and makes a session |
| 2 | Believe an ID token only once it is checked | `src/idToken.ts`: `verifyIdToken`, the algorithm, key and signature, then each claim. `src/jwks.ts`: `RemoteKeySet`, the provider's keys by `kid`, fetched again only for a `kid` it lacks |
| 3 | Refresh tokens that rotate, and a logout that revokes | `refreshTokens` and `revoke` in `src/provider.ts`. `refresh` keeps the token that comes back, and ends the session when the provider refuses. `logout` revokes, then redirects to `endSessionUrl` |
| 4 | The provider's session ends too, and no token is printed | Nothing new: the redirect of level 3 with `id_token_hint`, and log lines written as reasons. `postForm` never lets a parse error quote a body |

## Approach: reference (Check the state before the code, the signature before the claims, and keep only the newest refresh token)

### Intuition

Every step of this flow happens in a browser your app does not control, and each check exists because one step can be forged.

The callback is just a URL. Anyone can make a browser visit it, with a code of their own account: if your app redeemed it, the victim would be working in the attacker's account, and everything they typed would be the attacker's to read. The `state` is what ties a callback to the browser that started the login, so it is checked first, before the code is spent. The login attempt it belongs to is taken from the store as it is read, so it can be used once.

The code itself travels through the browser, in a URL that logs and history keep. A public client has no secret to prove at the token endpoint that it is the app that asked, so PKCE makes it prove something else: it sent a hash of a random verifier with the authorization request, and only it knows the verifier the hash came from. A code stolen on the way is worth nothing without it.

The ID token is a claim about who signed in, signed by the provider. Its header says how it was signed, and the header is written by whoever sent it, which is why the app decides the algorithm, `RS256`, and the key comes from the provider's own set by `kid`. Only once the signature holds do the claims mean anything: this provider, this client, not expired, and this login's `nonce`, so a token from another login cannot be replayed into this one.

Keys rotate. Fetching the provider's key set on every login works, and turns every login into two requests, which the provider pays for. Keeping the set forever works until the first rotation, when a token arrives signed with a key the app has never seen. The two meet in the middle: keep the set, and fetch it again exactly when a token names a `kid` it does not hold.

Refresh tokens rotate too, and the provider uses that to catch theft: a spent refresh token presented again means two parties hold the login, so it ends it for both. An app that keeps the old token is indistinguishable from a thief on its second refresh. And a logout has two ends: the app's session, and the provider's, which otherwise signs the next login in without asking. Revocation ends the login at the provider over the back channel; the redirect to `end_session_endpoint` clears the provider's cookie in the browser.

### Say it out loud

"On `/login` I make three random values: a state, a nonce and a PKCE verifier. I keep them server-side under a random id in an HttpOnly cookie, and redirect to the authorization endpoint with the state, the nonce and the SHA-256 of the verifier.

"On `/callback` I take the attempt out of the store, so it works once, and compare the state before anything else. Only then do I exchange the code, with the verifier.

"Then the ID token. I parse the header and refuse anything but RS256 with a kid. I look the kid up in the provider's key set, which I cache, refetching only when the kid is new. I verify the signature over the first two parts as they came. Then iss, aud, exp and iat with a minute of skew, and the nonce. Only then is there a session, and the browser gets a random session id, never a token.

"On refresh I always store the new refresh token. If the provider refuses, the login is over, and so is my session. On logout I revoke the refresh token and redirect to the end-session endpoint with the ID token as a hint, so the provider forgets the user too. And I never log a token, not even the one I refused."

### Algorithm

1. `/login`: make `state`, `nonce` and a verifier from 32 random bytes each; store them under a random id with an expiry; set the `login` cookie; redirect to `authorization_endpoint` with the S256 challenge.
2. `/callback`: take the attempt the cookie names and clear the cookie. No attempt, an expired one, or a different `state`: 400.
3. Exchange the code with the verifier. A refusal: 400.
4. Verify the ID token: `RS256` and a `kid`; the key by `kid`, fetching the set again if it is missing; the signature; `iss`, `aud` and `azp`, `exp` and `iat` with 60 s of skew, `nonce`. Any failure: 401.
5. Store the session with the user, the refresh token and the ID token; set the `session` cookie; redirect to `/`.
6. `/refresh`: send the refresh token; store the one that comes back. A refusal ends the session: 401.
7. `/logout`: take the session, revoke its refresh token, and redirect to `end_session_endpoint` with `id_token_hint`, `post_logout_redirect_uri` and `client_id`.

### Design

- `src/server.ts`: the routes as a lookup that answers 404 and 405 in one place, and the handlers. `callback` reads as the order of its checks, each with its status, through one `refuse` that clears the login cookie and logs the reason.
- `src/pkce.ts`: `randomValue` and `challengeOf`.
- `src/idToken.ts`: `verifyIdToken`, which takes a `KeySource`, so a test can hand it a key of its own. `InvalidToken` carries the rule that failed, never the token.
- `src/jwks.ts`: `RemoteKeySet`, a `Map` of public keys by `kid`, and one shared in-flight fetch, so two logins that meet a new `kid` together fetch once.
- `src/provider.ts`: the discovery document, fetched once, and the back-channel calls, each a form POST under a 5 s timeout. `TokenRefused` is the provider saying no; any other failure is the provider being unwell.
- `src/config.ts`, `src/cookies.ts` and `src/store.ts`: unchanged from the starter.

Not graded, and worth discussing:

- **Sessions in memory.** A restart signs everyone out here, while their logins live on at the provider. A real portal keeps sessions in a store, encrypted if they hold refresh tokens.
- **A confidential client.** A server-side app can hold a secret, or better a private key for `private_key_jwt`, and authenticate at the token endpoint as well as using PKCE. PKCE stays, because it also protects a code stolen in the browser.
- **Refetching on unknown kids.** As written, every token with a new random `kid` fetches the key set. A cooldown of a few seconds between refetches stops that, at the price of a short window after a real rotation.
- **Concurrent refreshes.** Two refreshes at once with the same token make the provider end the login. A per-session promise makes the second wait for the first and use its result.
- **The refreshed ID token.** The provider sends a new ID token with each refresh. The reference keeps the one from the login, which is still a valid `id_token_hint`. An app that uses the new one must verify it as it did the first, and check that its `sub` has not changed.

### Correctness

The login attempt is removed from the store in the same call that reads it, so a callback can succeed once, and the `state` comparison happens before `exchangeCode`, so a forged callback costs the provider nothing and spends no code. `verifyIdToken` refuses before it looks at a claim unless the header says `RS256`, the key comes from the provider's set and `verify` holds over the original bytes, so a token rewritten with `alg: none` or with one character of its signature changed is refused, and a token the provider signed for another audience, another login, or long expired is refused by the claim it breaks. `RemoteKeySet` only fetches when the `kid` is missing, so two logins with a known key fetch nothing, and a rotated key is found by one fetch. `refresh` writes the returned refresh token into the session before it answers, so the next refresh always sends the newest one. `logout` takes the session before anything else, so a failed revocation still ends it here.

### Complexity

- Time: per request — a login is three random values and a hash; a callback is one token request, and a key set fetch only on a `kid` the set lacks, plus one RSA verification
- Space: per session — one small record per session and per login in progress, and the provider's few public keys

### Trade-offs

The tokens live on the server, behind a random session id, so a script in the page cannot read them and a stolen cookie is only worth what the session is, until it ends. Putting them in the browser would spare the session store and expose every token to any script the page runs.

Checking the ID token in the app, with `node:crypto`, keeps every rule visible and costs about a hundred lines. A JOSE library would do the same with fewer lines and its own defaults, and the defaults are exactly where the classic mistakes live: an algorithm taken from the header, or an audience left unchecked.

Fetching the key set again on an unknown `kid`, with no expiry, finds a rotated key at once and never fetches otherwise. A periodic refresh would also notice a key the provider withdrew, which matters when a key leaks. A real client usually does both.

`POST /logout` revokes over the back channel and then redirects. Either alone leaves something behind: the redirect alone leaves a refresh token that works if the browser never arrives, and the revocation alone leaves the provider's cookie in the browser.

### Pitfalls and edge cases

**Wrong approaches.** Each fails a case, and the failure names what it did. Only correct solutions are stored, so these are described here.

| What it does | Why it is wrong | What catches it |
|--------------|-----------------|-----------------|
| No PKCE, or `code_challenge_method=plain` | The provider refuses the authorization request, so nobody can sign in | `v2`, at the provider, which answers its form only to a request it accepts, and every login |
| A verifier of 32 characters | The provider requires at least 43, and refuses the exchange | `v1`, at `/callback` |
| No `state` check | A callback with a forged state signs someone in | `h1`: `step 2 GET /callback: expected a 4xx status, got 302` |
| Keeps login attempts by their `state`, with no cookie | A callback that arrives in another browser signs that browser in | `h2` |
| Checks the `state` after the exchange | The code is spent for a callback that was never valid | `h1`, `h2`, by their count of code exchanges |
| Keeps the login attempt, and the `login` cookie, after the callback | The same callback again spends a second code | `h3`, by its count of code exchanges. Clearing the cookie alone passes it, since the grader's browser forgets a cleared cookie as a real one does |
| No `nonce` check | A token issued for another login is accepted | `h4` |
| Decodes the ID token without verifying it | Anyone who can change the token on its way signs in as anyone | `h5`, `h6` |
| Takes the algorithm from the token's header | A token that says `alg: none` needs no signature | `h6` |
| Fetches `jwks_uri` on every login | Two requests per login, and a provider that rate-limits its key set stops your logins | `v3`: `idp certs: expected at most 1 request, saw 2` |
| Fetches `jwks_uri` once and never again | The first token signed with a rotated key is refused, and nobody can sign in until a restart | `h9`, at the second login |
| No `aud` check | A token the provider issued to another client signs in here | `h7` |
| No `exp` check | An expired token, which may have leaked long ago, still signs in | `v4` |
| `exp` with no clock skew | A provider whose clock is a little ahead makes every login fail | `h8` |
| Keeps the first refresh token | The second refresh presents a spent token, and the provider ends the login | `h10`: `step 3 POST /refresh: status: expected 204, got 401` |
| Keeps the session, and its cookie, when the provider refuses a refresh | A revoked login lives on in your app | `h11`, at `GET /me` after the refused refresh |
| Clears the session without revoking | The refresh token still works at the provider | `v6`: `body: expected 0 elements, got 1; idp revoke: expected 1 request, saw 0` |
| Redirects to `end_session_endpoint` without `id_token_hint` | While the provider's session is alive, it asks the user to confirm, and the browser does not come back | None: the revocation just before has already ended that session, so the provider redirects without asking. It matters when a revocation fails |
| Logs the token response, or a refused token | Anyone with the log holds the user's login | `v8`, `h13`, `h14`: `app output: printed "eyJhbGciOiJSUzI1NiIs…", which matches eyJ…` |
| Logs a parse error of the provider's answer | `JSON.parse`'s message quotes the text it failed on, tokens included | None: no case breaks the provider's answers, so it is left to review |

**Edge cases.**

- A callback with `error=access_denied` and no code: the user said no at the provider. It is a 400, and the login attempt is spent.
- A login attempt that waited too long: the reference keeps attempts for ten minutes, as long as the cookie lives.
- A token response without `refresh_token` on refresh: allowed by OAuth, so the session keeps the old one.
- The key set holds an encryption key next to the signing ones; it signs nothing and is skipped.
