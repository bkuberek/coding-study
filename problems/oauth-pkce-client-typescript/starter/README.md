# Campus Portal

The campus portal's users sign in with the campus identity provider, by OpenID Connect's authorization code flow with PKCE. This is the start of the portal's side of that login: the routes are there, and the login itself is yours to build.

`cstudy` runs this service in a Docker sandbox, beside a real identity provider: your app sees this folder and nothing above it, and has no network beyond its stack.

## Running it

| Command | What it does |
|---------|--------------|
| `cstudy dev` | Runs your app with the identity provider, in the foreground, and prints its URL. Ctrl-C stops it. A browser cannot follow the login, since the provider's name exists only inside the sandbox, but `curl -i <url>/login` shows your redirect |
| `cstudy test` | Runs your tests beside the app, then the visible cases of your open levels, with the grader acting as the browser |
| `cstudy submit` | Grades every case of your open levels, and opens the next level when they pass |

The provider takes about half a minute to start. Your app reads `PORT` and listens on all interfaces inside the container (`0.0.0.0`). `/health` answers 200 once it is ready.

## What it reads

| Variable | Holds |
|----------|-------|
| `PORT` | The port to listen on |
| `OIDC_ISSUER` | The provider's issuer, `http://idp:8080/realms/campus`. Its discovery document is at `/.well-known/openid-configuration` under it |
| `OIDC_CLIENT_ID` | What the provider knows this app as, `portal` |

The provider's test user is `learner`, password `learner-pass`.

## Layout

| Path | Holds |
|------|-------|
| `src/server.ts` | The routes, and where the server starts |
| `src/config.ts` | The variables above, and the redirect URIs the provider registered for this app |
| `src/provider.ts` | `providerMetadata()`: the provider's endpoints, from its discovery document |
| `src/cookies.ts` | Reading the browser's cookies, and writing this app's |
| `src/store.ts` | `MemoryStore`: values in memory under random ids |
| `tests/` | Your tests |
| `vendors/idp/API.md` | The provider's contract, for reading |
| `.env` | What your app reads, written by `cstudy start`. Its environment already holds it |

The lock file is what the install uses, exactly. Add a dependency from a shell of your own and keep the lock with it.
