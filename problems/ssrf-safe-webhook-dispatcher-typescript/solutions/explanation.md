# SSRF-Safe Webhook Dispatcher (TypeScript): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | per request | per request | default answer: one function decides where a request may go, and every request, the first and each redirect, goes only where it said |

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | Register, deliver, sign, time out, cap the body | `webhookUrl` in `src/urls.ts`, `signature` in `src/signing.ts`, `send` and `bodyFits` in `src/delivery.ts`, the endpoint registry |
| 2 | Refuse internal destinations, at registration and at every delivery | `isInternal` in `src/addresses.ts` and `resolveDestination` in `src/destinations.ts`, called before every request |
| 3 | Redirects and retries | The redirect loop in `attemptDelivery`, which calls `resolveDestination` for every hop, and `worthRetrying` around it |
| 4 | A rate and one request in flight per host, and disabling | `HostRateLimiter` and `HostQueue` in `src/throttles.ts`, `Dispatcher`, and a failure count on `Endpoint` |

## Approach: reference (Resolve once, check every address, connect to what was checked)

### Intuition

A webhook URL is an instruction from a stranger: "send a request here". Everything this problem teaches comes from asking what "here" really is. It is not the text of the URL, which can spell `127.0.0.1` a dozen ways and hide it behind a user name. It is not even the host name, which is only a question for a resolver whose answers the stranger writes. "Here" is the address your socket connects to, and that is the only thing worth checking.

So the design has one gate. `resolveDestination` takes a parsed URL, looks its host up once, refuses it if any address is internal, and answers the address it checked. The request then goes to that address, never to the name, because a second lookup is a second answer, and an attacker who controls the name can make the first public and the second private. That is DNS rebinding, and the only defense is to connect to what you checked.

Redirects are the same problem again: a public server answers "go there instead", and "there" is a new instruction from a stranger. An HTTP client that follows redirects on its own goes there without asking. So the dispatcher follows them itself, and every hop passes the same gate as the first.

The limits are about the people you are not. A response can be as large as its sender likes, so you stop reading. A server can be as slow as it likes, so you stop waiting. And a customer can point a hundred endpoints at someone else's server, so the dispatcher counts per host, not per endpoint, and gives each host one request at a time.

### Say it out loud

"A URL from a customer tells my server where to send a request, so I have to decide where that really is. I parse the URL and judge the parsed form, since the text can disguise an address. Then I resolve the host once, refuse it if any of its addresses is private, loopback, link-local or the metadata address, and connect to the exact address I checked. I never let my HTTP client resolve the name again, because the attacker controls the name and can change its answer in between.

"I do this at registration, for a helpful error, and again before every request I send, since the answer can change after registration. Redirects go through the same check, hop by hop, because a public server can redirect anywhere: I turn off automatic following and follow at most three myself.

"Every request has a deadline that covers the body, and I stop reading a body past 64 KiB. I retry only what may pass, timeouts and 5xx, a bounded number of times with a wait. And I limit per destination host, not per endpoint, with one request in flight per host, so my service can't be used to flood someone else."

### Algorithm

1. Registration: check the request's fields, then the id, then parse the URL: `http` or `https`, no user name or password, an allowed port. Look the host up once and refuse it if it does not resolve or any address is internal. Store the URL as given, and the secret.
2. Delivery: serialize the event once and sign that exact text with each endpoint's secret.
3. For each endpoint, in its host's queue: skip it if it is disabled, then skip it if its host has had 5 deliveries in the last 10 s. Otherwise deliver.
4. An attempt: look the current URL's host up once, check every address, and send the request to the first, with a 1 s deadline and a 64 KiB cap on the body. A redirect status with a `Location` that is a URL webhooks may go to becomes the next hop, up to 3 times, and every hop goes through the same lookup and check.
5. Up to 3 attempts, 250 ms apart, after a timeout, a lost connection or a 5xx; anything else ends the delivery at once.
6. Count the outcome on the endpoint: a delivery resets its failures, a failure adds one, and the third in a row disables it.

### Design

- `src/server.ts`: the routes and the checks on request bodies, in the order the statement gives.
- `src/network.ts`: the starter's file, unchanged: the sandbox's resolver and its map from addresses to mock servers.
- `src/urls.ts`: `webhookUrl`, which parses and judges a URL, and resolves a redirect's `Location` against the URL that answered.
- `src/addresses.ts`: `isInternal`, one `net.BlockList` of every range the statement names.
- `src/destinations.ts`: `resolveDestination`, the one gate: one lookup, every address checked, the first address answered.
- `src/signing.ts`: `signature`, an HMAC-SHA256 of the exact body.
- `src/delivery.ts`: `deliver`, its attempts and their redirects, `send` with its deadline and `bodyFits` with its cap, and `worthRetrying`, a pure function.
- `src/endpoints.ts`: `Endpoint`, which counts failures in a row and is disabled at three, and `EndpointRegistry`.
- `src/throttles.ts`: `HostRateLimiter`, a sliding log per host, and `HostQueue`, a promise chain per host.
- `src/dispatcher.ts`: `Dispatcher`, which runs each endpoint through its host's queue, its limits and `deliver`, and keeps the results in order.
- `src/limits.ts`: every number the statement sets, in one place.

Not graded, and worth discussing:

- **Egress through a proxy.** Production dispatchers often send through a proxy that alone may reach the internet and enforces these rules, so a bug in one service cannot reach the metadata address. The application still has to follow redirects deliberately and limit what it sends.
- **Pinning in the client.** With `node:http`, a custom `lookup` on the agent can check the address the socket is about to use, which puts the check at the very point of connection. The reference reaches the same place more plainly, by connecting to the address it checked.
- **TLS.** Connecting to an address while the certificate names the host means passing the host name for SNI and verification separately, as `servername` does in `node:https`. The sandbox has no TLS, so the reference does not show it.
- **Persistence and a queue.** A real dispatcher stores deliveries and retries them over minutes or hours, from a queue, rather than inside one HTTP request. The rules for what to retry stay the same.

### Correctness

No request reaches an address that is not checked: `send` is the only place a request leaves, and its address comes only from `resolveDestination`, which answers an address only after every address of the host passed `isInternal`. Each hop of a redirect goes through `webhookUrl` and `resolveDestination` before `send`, so a redirect cannot skip either. The name is looked up once per request and never again, so no second answer can replace the checked one. Every number that bounds the work, 1 s, 64 KiB, 3 redirects, 3 attempts, holds per request or per delivery, so one delivery sends at most 12 requests, each given at most 1 s. The queue runs a host's deliveries one at a time and the limiter counts them as they start, so neither depends on how many endpoints share the host.

### Complexity

- Time: per request — at most 3 attempts of at most 4 requests each per endpoint, one lookup per request, and deliveries to different hosts at the same time
- Space: per request — one body of at most 64 KiB read per request in flight; the registry and the rate log grow with endpoints and hosts

### Trade-offs

Looking the host up again before every request costs a resolver round trip each time, and buys the one property that matters, that the address checked is the address used. Refusing a host when any of its addresses is internal is strict, and refuses a misconfigured customer who mixes one, where trying only the public addresses would be kinder and more code.

Following redirects at all is a choice: many dispatchers refuse them, which removes a whole class of attack at the cost of customers who moved a URL. Following them means each hop is new input from a stranger.

The rate limit keys on the host name, which a determined customer can spread across many names that share one address. Keying on the resolved address or the registrable domain closes that, at the cost of large customers who share hosting.

`node:http` and `fetch` keep the install small and the seams visible. A library that does SSRF filtering would do the same job, and is worth knowing about, but its defaults are where its bugs live, so read them.

### Pitfalls and edge cases

**Wrong approaches.** Each fails a hidden case, and the failure names what it did.

| What it does | Why it is wrong | What catches it |
|--------------|-----------------|-----------------|
| Refuses URLs whose text starts with `http://127.`, `http://10.`, `http://localhost` and so on | The same address has many spellings, and a name can lead anywhere | `h29`, `h30`, `h32`, `h39`: `status: expected 400, got 201`; `v6`, `h44` to `h50` |
| Checks the host name, or a literal address, but not the addresses a name resolves to | A stranger's name can resolve to your private network | `v6`, `h44` to `h50`, and `v8`: `internal-admin: expected 0 requests, saw 1` |
| Checks only the first address of a name | Another address may be the internal one | `h48` |
| Looks the name up to check it, and again to connect | The second answer can differ: that is DNS rebinding | `h52`: `internal-admin: expected 0 requests, saw 1` |
| Checks at registration, and never again | The name can change its answer after it was registered | `v8`, `h73` |
| Follows redirects with the HTTP client's own following | It goes wherever the redirect says, without asking | `v10`: here it leaves the sandbox's internet, and the result is not `blocked_destination` |
| Follows redirects itself, without checking each hop | A public first hop can redirect to the metadata address | `v10`, `h60`, `h61`: `internal-admin: expected 0 requests, saw 1` |
| Checks the first redirect, and not the ones after | A redirect chain only has to go wrong once | `h66` |
| Reads the whole body with `response.text()` | A server can send as much as it likes, and you hold all of it | `h22`: `error: expected "response_too_large", got null` |
| Retries every failure, a 4xx included | A 4xx answers the same every time, and each retry is load on the customer | `v11`, `h56`: `customer-hooks: expected 1 request, saw 3` |
| Retries at once | A struggling server gets the retries in the same instant | `v9`, `h53`: the gap |
| Retries a refused destination, a bad redirect or a body too large | None of them can change on a second try | `h22`, `h59`, `v10`: the count |
| Limits per endpoint rather than per host | A hundred endpoints at one host make a hundred times the traffic | `v12`, `h69`: `customer-hooks: expected 5 requests, saw 6` |
| `Promise.all` over every endpoint | Every endpoint at one host hits it at once | `h71`: `request 2 came before response 1` |
| Delivers one endpoint after another | Each slow host delays every other | `h72`: no answer within its 3 s |
| Counts a skipped delivery as a failure | A busy host would disable endpoints that never failed | `h74` |
| Never resets the count after a success | Three failures a week apart would disable a healthy endpoint | `h68` |

**Edge cases.**

- `https://hooks.shop.test@127.0.0.1/` is a URL whose user name is `hooks.shop.test` and whose host is `127.0.0.1`. Refusing user names and passwords outright removes the confusion (`h5`, `h6`).
- `2130706433`, `0x7f.1`, `0177.0.0.1` and `127.1` are `127.0.0.1` to a resolver and to the URL parser, and `0xa9fea9fe` is the metadata address (`h29` to `h32`, `h39`). Judge `url.hostname`, which the parser has already put in standard form.
- `0.0.0.0` reaches the local host on most systems, so `0.0.0.0/8` is internal (`h33`).
- `[::ffff:127.0.0.1]` is loopback over IPv6. The parser writes it as `[::ffff:7f00:1]`, so a check for the text `127.` misses it, and `net.BlockList` judges it by its IPv4 address (`h35`, `h47`).
- `172.16.0.0/12` runs from `172.16.0.0` to `172.31.255.255`, and `172.32.0.10` is public: a check on the text `172.` refuses a customer for nothing (`h42`, `h50`, `h51`).
- `localhost` is a name, not an address, and resolves to loopback like any other name could (`h43`).
- A relative `Location` is read against the URL that answered, and a redirect to itself must stop after 3 hops without a second attempt (`h58`, `h59`).
- Each attempt starts again from the endpoint's URL, so a 500 after a redirect costs a request at both hops each time (`h67`).
- A body of exactly 65,536 bytes is within the limit (`h23`). A check on `Content-Length` alone passes the cases, since the mock server always sends one, and fails against a server that sends its body in chunks.
- The signature is over the bytes sent. Re-serializing the event differently for the signature and the body, or signing before the keys are in their final order, breaks every customer's check (`h18`).
- An unknown endpoint in a delivery refuses the whole request before anything is sent, so a caller's typo never delivers half an event (`h17`).
