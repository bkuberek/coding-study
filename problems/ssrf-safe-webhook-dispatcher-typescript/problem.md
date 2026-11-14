# SSRF-Safe Webhook Dispatcher (TypeScript)

## Statement

Your service lets its customers register webhook URLs, and sends events to them: an invoice paid, a subscription renewed. The customer chooses the URL, and that makes your dispatcher a way into your own network. A URL can name `127.0.0.1`, a private address, or the cloud metadata address that hands out credentials. A name can resolve to one of them, change its answer between your check and your request, or redirect there after a public first hop. Making a server send a request it should not is server-side request forgery, SSRF.

Build the dispatcher in levels. It registers endpoints, delivers signed events within limits on time and size, refuses internal destinations however they are written, follows redirects and retries safely, and keeps one customer from turning it against someone else's server. `cstudy` runs your app in a Docker sandbox and judges it by what it answers over HTTP and by which mock servers it reached. The service, its hosts and their addresses are invented.

## Input

HTTP requests with JSON bodies: `POST /endpoints` and `GET /endpoints/{id}` to register and read an endpoint, and `POST /deliveries` to send an event. Each level says what it adds.

## Output

JSON, always with `Content-Type: application/json`. A refusal is `{"error": "<code>"}`, with the codes each level names. Your app reads its port from `PORT` and listens on all interfaces inside the container (`0.0.0.0`), and `GET /health` answers 200 once it is ready.

## Project

`cstudy start` copies the service into `projects/ssrf-safe-webhook-dispatcher-typescript/`, and `cstudy dev` runs it with its mock servers. Node runs the files by stripping their types, so write no `enum`, no `namespace` and no constructor parameter properties, and import your own files with their `.ts` extension.

- `src/server.ts`: the routes, and where the server starts. It registers endpoints without checking anything, and answers 501 to a delivery.
- `src/network.ts`: the sandbox's internet, below. You should not need to change it.
- `tests/`: your tests, run by `cstudy test`, with `tests/mockControl.ts` to set a mock server's visible scenario from a test and read what it received.
- `vendors/<name>/API.md`: what each mock server does, for reading. Nothing depends on these copies.
- `.env`: what your app reads, written by `cstudy start` from the problem's settings. Your app's environment already holds it.

`cstudy test` starts a sandbox, runs your tests beside the app, and then the visible cases of your open levels. `cstudy submit` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again, so a later change must keep their answers. To watch a failure yourself, run `cstudy dev --scenario customer-hooks=slow` and ask with `curl`.

### The sandbox's internet

Your app has no network beyond its stack, and Docker gives every mock server a private address, so a check on real addresses could not tell a customer's server from your own network. The problem therefore brings a small internet of its own, in `src/network.ts`, and your app reaches every host through it:

- `lookup(hostname)` answers every address a name resolves to, as a system resolver would. It asks the `resolver` mock server, whose `API.md` lists the names, and answers an IP address itself, in any spelling a resolver reads.
- `originFor(address)` gives the base URL of the mock server that plays an address. A request sent there, with the path and query of the URL you deliver to, stands for a connection to that address, whatever the URL's scheme and port.

| Address | Played by |
|---------|-----------|
| `203.0.113.10` | `customer-hooks`, a customer's server. Most names resolve here |
| `198.51.100.20` and `172.32.0.10` | `partner-hooks`, another customer's server |
| Any other address | `internal-admin`, your company's own network |

That is the line a real dispatcher draws: look the name up, check the address, and connect to the address you checked. The cases judge it from the mock servers' logs, and a request that reaches `internal-admin` is one a customer's URL tricked your app into sending. The public addresses come from ranges kept for documentation, `203.0.113.0/24` and `198.51.100.0/24`, and in this problem they are public.

## Level 1: Register and deliver

`POST /endpoints` registers where a customer wants events sent:

```json
{"id": "shop-1", "url": "https://hooks.shop.test/events", "secret": "whsec-0123456789abcdef"}
```

| Field | Rule |
|-------|------|
| `id` | 1 to 64 letters, digits, `-` or `_` |
| `url` | Where events go, a URL webhooks may go to |
| `secret` | At least 16 characters: the key the customer checks signatures with |

It answers 201 with the endpoint, which shows the URL as it was given and never the secret:

```json
{"id": "shop-1", "url": "https://hooks.shop.test/events", "status": "active", "consecutive_failures": 0}
```

`GET /endpoints/{id}` answers 200 with the same shape. `consecutive_failures` counts the endpoint's failed deliveries since its last delivered one.

A URL webhooks may go to parses as an absolute URL with the scheme `http` or `https`, no user name or password, and the port 80, 443, 8080 or 8443, written or implied by the scheme. Judge the parsed URL, never its text: `https://hooks.shop.test@127.0.0.1/` starts like a customer's URL, and its host is `127.0.0.1`.

| Request | Status | Body |
|---------|--------|------|
| A body that is not a JSON object, or a field missing or breaking its rule | 400 | `{"error": "invalid_request"}` |
| An `id` already registered | 409 | `{"error": "endpoint_exists"}` |
| A `url` that is not one webhooks may go to | 400 | `{"error": "invalid_url"}` |
| `GET` of an id never registered | 404 | `{"error": "unknown_endpoint"}` |

A registration is checked in the order of this table.

`POST /deliveries` sends one event to some endpoints:

```json
{"endpoints": ["shop-1"], "event": {"id": "evt_1001", "type": "invoice.paid", "data": {"invoice": "inv_77", "amount_cents": 4200}}}
```

`endpoints` lists 1 to 10 different ids and `event` is a JSON object; anything else is 400 `invalid_request`. An id never registered is 404 `unknown_endpoint`, and then nothing is sent to anyone. Otherwise your app sends each endpoint one request:

- `POST` to the endpoint's URL, through `lookup` and `originFor`;
- the event as compact JSON, its keys in the order they came, which is what `JSON.stringify` gives;
- `Content-Type: application/json`;
- `X-Webhook-Signature: sha256=<hex>`, the HMAC-SHA256 of that exact body, keyed with the endpoint's secret.

A request has 1 s, from connecting to the last byte of the answer. Read at most 65,536 bytes of the answer's body, and stop reading as soon as it passes that. A 2xx delivers.

It answers 200 with one result per endpoint, in the order the request named them:

| Field | Meaning |
|-------|---------|
| `endpoint` | The endpoint's id |
| `status` | `delivered` or `failed`, and from level 4 `skipped` |
| `response_status` | The status of the last answer your app received for it, or `null` when none came |
| `error` | `null` when delivered, otherwise why, as below |
| `signature` | The `X-Webhook-Signature` value for this endpoint and event |

| What happened | `error` |
|---------------|---------|
| No whole answer within 1 s | `timeout` |
| No connection | `connection_failed` |
| A body over 65,536 bytes | `response_too_large` |
| A status that is not 2xx | `bad_status` |

### Example 1

<!-- case: v1 -->

A valid URL is registered, and the answer shows everything but the secret.

### Example 2

<!-- case: v2 -->

`v2` was registered first, at `https://v2.shop.test/events` with the secret `whsec-0123456789abcdef`. The delivery sends one request to `customer-hooks`, and the signature is the one that request carried.

### Example 3

<!-- case: v3 -->

An `ftp` URL is not one webhooks may go to.

### Example 4

<!-- case: v4 -->

`v4` was registered first, at `https://v4.shop.test/events`, and `customer-hooks` takes 1.5 s to answer: past the 1 s a request has, so the delivery fails with no answer.

## Level 2: Block internal destinations

The customer chooses the URL, so the customer chooses where your app sends a request. Refuse every address in these ranges:

| Range | What lives there |
|-------|------------------|
| `0.0.0.0/8` | "This network": a connection to `0.0.0.0` reaches the host itself |
| `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` | Private networks |
| `100.64.0.0/10` | Shared address space, behind a carrier's NAT |
| `127.0.0.0/8` | Loopback |
| `169.254.0.0/16` | Link-local, with the cloud metadata address `169.254.169.254` |
| `224.0.0.0/4` and `240.0.0.0/4` | Multicast, and reserved addresses with the broadcast address |
| `::` and `::1` | The unspecified IPv6 address, and IPv6 loopback |
| `fc00::/7`, `fe80::/10`, `ff00::/8` | IPv6 unique local, link-local and multicast |

An IPv4-mapped IPv6 address, `::ffff:a.b.c.d`, is judged by the IPv4 address inside it. Every other address is public.

An IP address can be written many ways that a resolver reads as one: `2130706433`, `0x7f.1`, `0177.0.0.1` and `127.1` are all `127.0.0.1`. The URL parser writes each the standard way in `url.hostname`, so judge that.

- **Registering.** Look the host up once. A name that does not resolve answers 400 with `{"error": "unresolvable_host"}`, and a host with any internal address 400 with `{"error": "blocked_destination"}`. Both come after `invalid_url`.
- **Delivering.** Look the host up again for each request you send, once, check every address, and connect to the first: the one you checked. Never look the name up a second time for the same request. The name's owner chooses each answer, and can change it between your check and your request. A delivery refused this way fails with `unresolvable_host` or `blocked_destination`, and sends nothing.

### Example 1

<!-- case: v5 -->

Loopback, written plainly.

### Example 2

<!-- case: v6 -->

`intranet.attacker.test` looks like any other customer's name, and it resolves to `10.20.0.5`.

### Example 3

<!-- case: v7 -->

`nowhere.test` has no address at all.

### Example 4

<!-- case: v8 -->

With the resolver's `rebinding` scenario, `rebind.attacker.test` answered `203.0.113.10` when `v8` was registered, and answers `10.20.0.5` after that. The delivery looks it up again, refuses, and sends nothing: the resolver is asked twice in all, and `internal-admin` receives nothing.

## Level 3: Redirects and retries

A public server can answer with a redirect to an internal one. Follow 301, 302, 303, 307 and 308 yourself, never with your HTTP client's own following, and check every hop as you checked the first:

- Send the same request again, with the same method, body and headers, to the `Location`, read relative to the URL that answered.
- The `Location` must be a URL webhooks may go to, and its host is looked up once and checked, as in level 2.
- Follow at most 3 redirects. A fourth fails the delivery with `too_many_redirects`.

| The redirect | `error` |
|--------------|---------|
| No `Location`, or one that is not a URL webhooks may go to | `invalid_redirect` |
| A host that does not resolve | `unresolvable_host` |
| A host with an internal address | `blocked_destination` |

`response_status` is then the redirect's own status, since it was the last answer.

A delivery now makes up to 3 attempts. Each starts again from the endpoint's URL and follows its own redirects. Try again only after an attempt that ended with `timeout`, `connection_failed`, or `bad_status` with a 5xx, and wait at least 250 ms after it first. Nothing else is tried again: a 4xx will not change, and neither will a refused destination, a redirect that cannot be followed or a body that is too large. The result is that of the last attempt.

### Example 1

<!-- case: v9 -->

`customer-hooks` answers 503 twice, then 200: the delivery takes 3 requests, at least 250 ms apart.

### Example 2

<!-- case: v10 -->

`customer-hooks` answers 302 with `Location: http://169.254.169.254/metadata/credentials`. The redirect is the last answer, after one request, and `internal-admin` receives nothing.

### Example 3

<!-- case: v11 -->

`customer-hooks` answers 410 to everything: one request, and no second.

## Level 4: Abuse limits

A customer can register many endpoints at one host, and point them at a server that is not theirs. Your dispatcher must not become the way to flood it. A host here is the URL's host name, as the URL parser gives it.

- **One request in flight per host.** The endpoints of one delivery go out at the same time, except that deliveries to one host go one after another, in the order the request names them.
- **At most 5 deliveries per host in any 10 s.** One more is `skipped` with `rate_limited`, and nothing is sent. The limit counts the deliveries your app started, across endpoints and requests.
- **Three failures in a row disable an endpoint.** When `consecutive_failures` reaches 3, the endpoint's `status` becomes `disabled` for good, and each later delivery to it is `skipped` with `endpoint_disabled`, with nothing sent. A disabled endpoint is skipped before the rate is counted.

A skipped delivery does not count toward the rate, and is not a failure. Its result has `"response_status": null`, and still carries its `signature`.

### Example 1

<!-- case: v12 -->

Six endpoints, `v12-a` to `v12-f`, were registered first, all at `https://v12.shop.test/events`. In one delivery the first five go out, `v12-f` is skipped, and `customer-hooks` receives 5 requests.

### Example 2

<!-- case: v13 -->

`customer-hooks` answers 410 to everything, and `v13` has just failed three deliveries in a row.

### Example 3

<!-- case: v14 -->

The same for `v14`, and then one more delivery: it is skipped, and `customer-hooks` still has only the 3 requests of the failures.

## Constraints

- Your app reaches hosts only through `lookup` and `originFor`.
- It never sends a request to an internal address: the cases count what `internal-admin` receives, and expect nothing.
- One lookup per request it sends, and one per registration: the cases count what the resolver receives.
- At most 3 attempts per delivery, and 4 requests per attempt: the first and 3 redirects.
- A wait never comes up short: the cases measure the gap between an answer and your next request.

## Follow-ups

- Delivery looks the name up again rather than keeping the address from registration. What would pinning that address protect, and what would it break when a customer moves to a new server?
- The rate limit counts per host name, and one customer can own `a.shop.test`, `b.shop.test` and a thousand more at one address. What would you count instead, and what would that cost a large customer?
- Many teams send webhooks through an egress proxy that alone holds these rules. What does that move out of your code, and what does it still leave to it?
- The signature covers only the body, so a receiver cannot tell a fresh delivery from one an attacker recorded and sent again. What would a timestamp in the signed text change, and what must the receiver then check?
- A retry here waits a fixed 250 ms. Why do real dispatchers wait longer each time, with some randomness, and what does a receiver see when a thousand deliveries retry at the same moment?
- A disabled endpoint stays disabled. How should its customer find out, and how should they get it back?

## Hints

### Hint 1

Write one function that takes a parsed URL and answers either an address to connect to or a refusal. Registration, every delivery and every redirect call it, so no path can skip it.

### Hint 2

Parse first, judge after. `new URL()` turns `0x7f.1` into `127.0.0.1` and `[::ffff:127.0.0.1]` into `[::ffff:7f00:1]`, and `net.BlockList` checks an address against subnets, IPv4-mapped addresses included.

### Hint 3

With `redirect: "manual"`, `fetch` hands you a redirect as an ordinary answer, `Location` header and all. Then the loop that follows it is yours, and so is the check on each hop.

### Hint 4

`response.text()` reads the whole body before you can count it. Read `response.body` a chunk at a time and stop once the count passes the limit. `AbortSignal.timeout(1000)` on the request covers the body too.

### Hint 5

For level 4, chain each host's deliveries on one promise, so they run one at a time, and wait for all the chains with `Promise.all`, which keeps the results in order while hosts run at once.
