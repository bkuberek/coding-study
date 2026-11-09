# OAuth Client with PKCE (TypeScript)

## Statement

A campus runs one identity provider for all its web apps, and the campus portal is one of them. Nobody types a password into the portal: it sends each user to the provider, the provider signs them in on its own page, and sends them back with a one-time code. The portal trades that code for tokens over a back channel, believes the ID token only once it has checked it, and keeps a session of its own. This is OpenID Connect's authorization code flow, and the portal is the client.

The provider registered the portal as a public client, with no secret, so PKCE is what proves that the app redeeming a code is the one that asked for it. Build the portal's side of the login, in levels: the flow with PKCE, `state` and `nonce`; an ID token checked against the provider's own keys, which it rotates; refresh tokens that rotate too; and a logout that ends the login everywhere, without a token ever reaching your app's output.

`cstudy` runs your app in a Docker sandbox with a real identity provider, Keycloak, signing every token. The grader acts as the browser: it follows your redirects, fills in the provider's login form as the user `learner`, and comes back to your callback. To make the provider misbehave the way real ones do, it also uses the provider's admin API, to rotate its signing key, or to have it sign a token for another audience or one that has expired. Between your app and the provider stands a mock server, `idp`, that passes every request through and logs it, so a case can count what your app asked for, and that can spoil a token on its way back. The campus, the portal and the user are invented.

## Input

HTTP requests from the browser: `GET /login`, the browser's return to `GET /callback`, and `GET /me`, `POST /refresh` and `POST /logout` from a signed-in browser. Your app finds the provider at `OIDC_ISSUER`, `http://idp:8080/realms/campus`, and is known to it as `OIDC_CLIENT_ID`, `portal`. `vendors/idp/API.md` describes every endpoint of the provider your app uses: read it first.

## Output

JSON, with `Content-Type: application/json`, a redirect, or both. Your app reads its port from `PORT` and listens on all interfaces inside the container (`0.0.0.0`), and `GET /health` answers 200 once it is ready.

| Request | With a session | Without one |
|---------|----------------|-------------|
| `GET /login` | 302 to the provider (level 1) | The same |
| `GET /callback` | 302 to `/` with a new session, or a 4xx (level 1) | The same |
| `GET /me` | 200 with the user | 401 `{"error": "not signed in"}` |
| `POST /refresh` | 204 (level 3) | 401 `{"error": "not signed in"}` |
| `POST /logout` | 302 to the provider (level 3) | 401 `{"error": "not signed in"}` |
| `GET /` | 200 `{"app": "campus portal", "signed_in": true}` | The same, with `false` |

`GET /me` answers who signed in, from their ID token's claims `sub`, `preferred_username` and `email`, and nothing else:

```json
{"sub": "93b7b2cd-9b05-4904-8716-3ca8ffb65e55", "username": "learner", "email": "learner@campus.example"}
```

A refusal is a 4xx with `{"error": "..."}`, whose text is yours: say why, for whoever reads it. The cases check the status class and what your app does next, not the words.

## Project

`cstudy start` copies the service into `projects/oauth-pkce-client-typescript/`. Node runs the files by stripping their types, so write no `enum`, no `namespace` and no constructor parameter properties, and import your own files with their `.ts` extension. Everything here needs only Node: `fetch` for the provider, and `node:crypto` for random values, hashes and signatures. No JOSE or OAuth library is installed, and none is needed.

- `src/server.ts`: the routes, and where the server starts. `/health`, `/` and `/me` work already; `/login`, `/callback`, `/refresh` and `/logout` answer 501.
- `src/config.ts`: what your app reads from its environment, and the two URLs the provider registered for it: `REDIRECT_URI`, `http://app:8000/callback`, and `POST_LOGOUT_REDIRECT_URI`, `http://app:8000/`.
- `src/provider.ts`: `providerMetadata()`, the provider's endpoints from its discovery document, fetched once.
- `src/cookies.ts`: `readCookies`, `cookie` and `clearedCookie`, for the cookies your app sets: each is `HttpOnly` and `SameSite=Lax`.
- `src/store.ts`: `MemoryStore`, values kept in memory under random ids, for a cookie to point at. There is no database.
- `tests/`: your tests, run by `cstudy test`.
- `vendors/idp/API.md`: the provider's contract, for reading. Nothing depends on this copy.
- `.env`: what your app reads, written by `cstudy start` from the problem's settings. Your app's environment already holds it.

`cstudy test` starts a sandbox, runs your tests beside the app, and then the visible cases of your open levels. `cstudy submit` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again. The provider takes about half a minute to start in each sandbox, and that time counts toward no case. Its state lasts for the whole run, so each case starts its own logins, and a case that changes the provider puts it back.

**Your browser cannot log in.** The provider lives at `http://idp:8080` and your callback at `http://app:8000/callback`: names that exist only inside the sandbox, and the provider writes every URL with them. `cstudy dev` runs your app with the provider all the same, and prints your app's URL, so `curl -i <url>/login` shows the redirect your app builds. To see a whole login work, run `cstudy test`: the grader is the browser.

## Level 1: Sign in with the code flow and PKCE

`GET /login` starts a login. Make three random values, each from at least 32 random bytes: a `state`, a `nonce`, and a code verifier of 43 to 128 characters (`randomBytes(32).toString("base64url")` gives 43). Keep them on the server, under a random id that a `login` cookie carries, and answer 302 to the provider's `authorization_endpoint` with:

| Parameter | Value |
|-----------|-------|
| `client_id` | `OIDC_CLIENT_ID` |
| `response_type` | `code` |
| `redirect_uri` | `REDIRECT_URI` |
| `scope` | `openid` |
| `state` | The state |
| `nonce` | The nonce |
| `code_challenge` | The SHA-256 of the verifier, as base64url without padding |
| `code_challenge_method` | `S256` |

The provider signs the user in and sends the browser to `GET /callback?state=...&code=...`. There, take the login attempt the `login` cookie points at, so that it is gone whatever happens next, and clear the cookie. Then, in this order:

1. With no login attempt, or a `state` that is not its state, answer 400 and stop. The code is not spent.
2. Exchange the code at the provider's `token_endpoint`, with the attempt's verifier. A refusal is a 400.
3. Read the ID token's claims, the middle part of the JWT as base64url JSON, and refuse it with a 401 unless its `nonce` is the attempt's. Level 2 checks the rest of it.
4. Keep a session on the server, with the user from the claims and the tokens, under a random id that a `session` cookie carries, and answer 302 to `/`.

A refused callback makes no session. The browser never sees a token: it holds only the two ids.

- The `state` ties the callback to the browser that started the login. Without it, anyone can send you a link to the callback with a code of their own account, and you would be signed in as them.
- The `nonce` ties the ID token to this login, so a token issued for another login cannot be passed off as this one's.
- PKCE ties the code to your app: only the holder of the verifier can redeem it. The provider refuses a request without `code_challenge`, or with `code_challenge_method=plain`.

### Example 1

<!-- case: v1 -->

The browser asks for `GET /login`, follows the redirect, and the provider's form signs `learner` in. The provider sends it to `/callback` with a code, your app answers 302 to `/`, and then `GET /me` answers 200 with `{"sub": "93b7b2cd-9b05-4904-8716-3ca8ffb65e55", "username": "learner", "email": "learner@campus.example"}`.

### Example 2

<!-- case: v2 -->

`GET /login` answers 302 to `http://idp:8080/realms/campus/protocol/openid-connect/auth?client_id=portal&response_type=code&redirect_uri=http%3A%2F%2Fapp%3A8000%2Fcallback&scope=openid&state=...&nonce=...&code_challenge=...&code_challenge_method=S256`, and the provider answers that URL with its login form, 200.

## Level 2: Trust the ID token

An ID token is a claim about who signed in, and only the provider's signature makes it true. Before your app believes it, check, in this order:

| Check | Refuse when |
|-------|-------------|
| The header | Its `alg` is not `RS256`, or it names no `kid`. The header is written by whoever sent the token, so it never chooses the algorithm |
| The key | The provider's key set, at `jwks_uri`, has no key with that `kid` |
| The signature | `verify("sha256", <header>.<payload>, key, <signature>)` from `node:crypto` fails, with the key from `createPublicKey({key: jwk, format: "jwk"})` |
| `iss` | It is not `OIDC_ISSUER` |
| `aud` | It is not `OIDC_CLIENT_ID`, or a list without it. A list of several must also have `azp` equal to `OIDC_CLIENT_ID` |
| `exp` | Now is more than 60 s past it |
| `iat` | It is more than 60 s ahead of now |
| `nonce` | It is not the login attempt's |

A refused ID token is a 401 at `/callback`, with no session.

Fetch the key set once and keep it. Fetch it again only for a `kid` it does not hold, then look once more: the provider rotates its signing key without notice, and the first token signed with a new key carries a `kid` you have not seen. The provider's clock and your app's may differ by up to 60 s, which is all the slack `exp` and `iat` get.

### Example 1

<!-- case: v3 -->

Two browsers sign in, one after the other, and each gets 200 from `GET /me`. Between them your app asks the provider's `jwks_uri` at most once: once if its key set was empty, and not at all if it already held the key.

### Example 2

<!-- case: v4 -->

The provider is set to issue tokens that expired ten minutes before they were issued. After the provider's form, `/callback` answers a 4xx, and `GET /me` answers 401.

## Level 3: Refresh and revoke

An access token lives five minutes, and the refresh token is how your app gets new ones without sending the user to the provider again. A real app refreshes when it needs a fresh access token; here `POST /refresh` asks for it, so a case decides when.

`POST /refresh` sends the session's refresh token to `token_endpoint` and answers 204. The provider rotates refresh tokens: each refresh answers a new one and spends the one it was sent, so keep the new one in the session. A spent refresh token presented again is taken as stolen, and the provider ends the whole login. When the provider refuses a refresh, because the login has ended or was revoked, end the session here too, and answer 401 with `{"error": "session ended"}`.

`POST /logout` ends the session, then:

1. Revokes the session's refresh token at the provider's `revocation_endpoint`. That ends the login at the provider, so nothing your app held can be used again. A revocation that fails still logs the user out here.
2. Answers 302 to the provider's `end_session_endpoint`, with `id_token_hint` set to the session's ID token, `post_logout_redirect_uri` set to `POST_LOGOUT_REDIRECT_URI`, and `client_id`. The browser goes there to end the provider's own session (level 4).

Without a session, both answer 401 with `{"error": "not signed in"}`, and call the provider not at all.

### Example 1

<!-- case: v5 -->

After a login, `POST /refresh` answers 204, your app has called `token_endpoint` with `grant_type=refresh_token` once, and `GET /me` still answers 200.

### Example 2

<!-- case: v6 -->

After a login, `POST /logout` answers 302. Then `GET /me` answers 401, your app has called `revocation_endpoint` once, and the provider's admin API lists no session for `learner`.

## Level 4: Sign out and keep tokens secret

The provider keeps a session of its own, in its own cookie in the browser. Until it ends, the next `GET /login` comes straight back with a code, without the login form: anyone at that browser is signed in again. So the logout of level 3 ends with the provider. With `id_token_hint` and the registered `post_logout_redirect_uri`, it ends its session and sends the browser back to `http://app:8000/` at once. Without the hint, while its session is alive, it asks the user to confirm on a page of its own instead, and it refuses any other redirect URI.

A token in a log is a token anyone with the log can use: an access token calls APIs as the user, a refresh token makes new ones, and a code may still be unspent. Your app prints none of them, nor any authorization code, on its standard output or error, not even when something fails: a refused token is exactly what an error message is tempted to quote. Print why instead. The grader reads everything your app prints while a case runs.

### Example 1

<!-- case: v7 -->

After a login, the browser follows `POST /logout`'s redirect to the provider, which answers 302 straight back to `http://app:8000/`. `GET /me` answers 401, and a new `GET /login` leads to the provider's login form again.

### Example 2

<!-- case: v8 -->

A login, a refresh and a logout, and nothing your app printed meanwhile holds a JWT (`eyJ...` `.` `eyJ...`) or the login's authorization code.

## Constraints

- The browser holds random ids, never a token. Every cookie your app sets is `HttpOnly` and `SameSite=Lax`.
- A login attempt is used once, and its `state` is checked before its code is spent.
- An ID token is believed only after its signature, with `RS256` and a key from `jwks_uri`, and then `iss`, `aud`, `exp`, `iat` and `nonce`, with 60 s of clock skew.
- `jwks_uri` is fetched once, and again only for a `kid` your app does not hold.
- Only the newest refresh token is kept.
- Nothing your app prints holds a token or a code.
- Your app reaches the provider only through `OIDC_ISSUER` and the endpoints its discovery document names, and listens on all interfaces inside the container.

## Follow-ups

- Two tabs of the same browser refresh at the same moment, with the same refresh token. What does the provider do with the second, and how would you make the second wait for the first?
- An attacker sends your callback tokens with a new random `kid` each time. What does your key set do, and how would you limit it without breaking a real rotation?
- Your app restarts and loses its memory. Who is still signed in, at the provider and here, and what would a session store have to hold?
- The portal grows a single-page front end that calls the portal's API. Where do the tokens live now, and why do many teams keep them on the server anyway?
- The provider can tell your app that a user logged out elsewhere, by back-channel logout. What would your app need to keep to find and end that user's session?

## Hints

### Hint 1

Keep the login attempt in a `MemoryStore` and read it with `take`, so a second callback with the same cookie finds nothing. Clear the `login` cookie in every answer of `/callback`.

### Hint 2

`new URL(endpoint)` with `url.search = new URLSearchParams({...}).toString()` builds a redirect with every value encoded. `fetch(url, {method: "POST", body: new URLSearchParams({...})})` sends a form.

### Hint 3

A JWT is three base64url parts joined by dots. `Buffer.from(part, "base64url")` decodes one. The signature covers the first two parts exactly as they came, dot included, not anything you decoded and encoded again.

### Hint 4

The key set holds keys that sign (`"use": "sig"`) and keys that encrypt. Keep the signing ones in a `Map` by `kid`, and when a `kid` is missing, fetch the set and look again. Nothing more: no schedule, no expiry.

### Hint 5

An error message can quote what it failed on. Log your own words: "the ID token's signature does not hold", not the token, and not the provider's whole answer.
