# The identity provider

The campus's OpenID Connect provider. It knows your app as the client `portal`, signs users in on its own login page, and issues the tokens your app trusts. Your app reaches it at `OIDC_ISSUER`, `http://idp:8080/realms/campus`, and finds every endpoint from there. This is its contract, and it will not change for you.

In the sandbox it is Keycloak 26.8.2, a real identity provider, so everything below is enforced by the provider itself, not by `cstudy`.

## Discovery

`GET {OIDC_ISSUER}/.well-known/openid-configuration` answers 200 with the provider's metadata. Your app needs these fields:

| Field | Value here |
|-------|------------|
| `issuer` | `http://idp:8080/realms/campus`, exactly the `iss` of every token |
| `authorization_endpoint` | `http://idp:8080/realms/campus/protocol/openid-connect/auth` |
| `token_endpoint` | `http://idp:8080/realms/campus/protocol/openid-connect/token` |
| `jwks_uri` | `http://idp:8080/realms/campus/protocol/openid-connect/certs` |
| `revocation_endpoint` | `http://idp:8080/realms/campus/protocol/openid-connect/revoke` |
| `end_session_endpoint` | `http://idp:8080/realms/campus/protocol/openid-connect/logout` |

Read them from the document rather than building them: they are the provider's to change.

## The client `portal`

| Setting | Value |
|---------|-------|
| Type | Public: it has no secret, so every request names it with `client_id=portal` |
| Grant | The authorization code flow only |
| PKCE | Required, with the `S256` method. An authorization request without `code_challenge`, or with `code_challenge_method=plain`, is refused |
| Redirect URI | `http://app:8000/callback`, exactly |
| Post-logout redirect URI | `http://app:8000/`, exactly |
| Scopes | `openid`. The `profile` and `email` claims come with it by default |

## The authorization request

Your app sends the browser to `authorization_endpoint` with these query parameters:

| Parameter | Value |
|-----------|-------|
| `client_id` | `portal` |
| `response_type` | `code` |
| `redirect_uri` | `http://app:8000/callback` |
| `scope` | `openid` |
| `state` | A value your app checks when the browser comes back |
| `nonce` | A value the provider copies into the ID token |
| `code_challenge` | The base64url SHA-256 of your code verifier, without padding |
| `code_challenge_method` | `S256` |

The provider shows its login page. When the user signs in, it redirects the browser to `http://app:8000/callback?state=...&session_state=...&iss=...&code=...`. A refused request redirects there with `error` and `error_description` in place of `code`.

The test user is `learner`, password `learner-pass`.

## `POST token_endpoint`

A form body (`application/x-www-form-urlencoded`). To exchange a code:

| Field | Value |
|-------|-------|
| `grant_type` | `authorization_code` |
| `code` | The code from the callback |
| `redirect_uri` | `http://app:8000/callback`, the same as in the authorization request |
| `client_id` | `portal` |
| `code_verifier` | The verifier whose challenge the authorization request carried: 43 to 128 characters of `A-Z`, `a-z`, `0-9`, `-`, `.`, `_` and `~` |

To refresh: `grant_type=refresh_token`, `refresh_token` and `client_id=portal`.

It answers 200 with JSON:

```json
{"access_token": "eyJ...", "expires_in": 300, "refresh_expires_in": 1800, "refresh_token": "eyJ...",
 "token_type": "Bearer", "id_token": "eyJ...", "not-before-policy": 0, "session_state": "...", "scope": "openid profile email"}
```

Or 400 with `{"error": "invalid_grant", "error_description": "..."}`. Among the reasons:

- A code is valid once, for a minute. A second exchange, or one with the wrong verifier, is refused, and a failed exchange spends the code.
- **Refresh tokens rotate.** Each refresh answers a new `refresh_token`, and the one it was given is spent. Presenting a spent refresh token is taken as theft: it is refused, and the whole login it belongs to ends, so the newest refresh token stops working too.
- A refresh token of a login that has ended, by logout or by revocation, is refused.

## The ID token

A JWT signed with RS256. Its header names the signing key by `kid`:

```json
{"alg": "RS256", "typ": "JWT", "kid": "JjCnaXZm3L2qzJ-qRG_4-f82S3om4HrIjHBWRr2y1lE"}
```

Its claims, among others:

```json
{"iss": "http://idp:8080/realms/campus", "aud": "portal", "azp": "portal", "sub": "93b7b2cd-9b05-4904-8716-3ca8ffb65e55",
 "nonce": "...", "iat": 1794265256, "exp": 1794265556, "preferred_username": "learner", "email": "learner@campus.example"}
```

An ID token lives 300 s. The provider's clock and your app's may differ by up to 60 s.

## `GET jwks_uri`

The public keys that verify the provider's signatures, as a JSON Web Key Set:

```json
{"keys": [{"kid": "JjCnaXZm3L2qzJ-qRG_4-f82S3om4HrIjHBWRr2y1lE", "kty": "RSA", "alg": "RS256", "use": "sig", "n": "...", "e": "AQAB"},
          {"kid": "hAz3GH...", "kty": "RSA", "alg": "RSA-OAEP", "use": "enc", "n": "...", "e": "AQAB"}]}
```

Only keys with `"use": "sig"` sign tokens. The provider rotates its signing keys without notice: a new key appears in this set, and new tokens carry its `kid` from that moment. A key it stops using for new tokens stays in the set for a while, so tokens it signed still verify.

## `POST revocation_endpoint`

A form body: `token`, `token_type_hint=refresh_token` and `client_id=portal`. Revoking a refresh token ends the login it belongs to at the provider. It answers 200 with an empty body.

## `GET end_session_endpoint`

The browser's logout at the provider. With `id_token_hint` (an ID token of the login), `post_logout_redirect_uri=http://app:8000/` and `client_id=portal`, it ends the provider's own session, the one that would sign the user in again without the login page, and redirects the browser to `http://app:8000/` at once. Without `id_token_hint`, while its session is still alive, it shows a page asking the user to confirm. A `post_logout_redirect_uri` that is not registered is refused with an error page.
