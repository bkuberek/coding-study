# CORS Policy Evaluator: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| serialize-then-match | optimal | O(P L) per request | O(C) | default answer |

`L` is the length of the request's values, `P` the number of patterns and `C` the size of the configuration (origins, patterns, methods and headers).

## How the design grows level by level

| Level | Change | What the policy adds |
|-------|--------|----------------------|
| 1 | Origins | A serializer for URLs and a set of serialized origins; the decision is one lookup |
| 2 | Preflights | The browser's safelist, as a function per header, and a server answer that is all or nothing |
| 3 | Credentials | One origin decision with four ordered rules, from which the credentials header, `Vary` and the method and header wildcards all follow |
| 4 | Patterns and lint | A second way to be "listed" that plugs into the same decision, and a report over the configuration |

The early choice that matters is to serialize every configured origin when it is added. The browser always sends a serialized origin and compares the answer byte for byte, so once the configuration is in the same form, deciding needs no parsing of the request at all, and no normalization that an unusual header could abuse.

## Approach: serialize-then-match (Serialize origins once then decide by exact lookups and one pattern scan)

### Intuition

CORS is a handshake in which the server only ever echoes: it reads `Origin`, decides, and either writes that same value back in `Access-Control-Allow-Origin`, or `*`, or nothing. Every security property comes from *when* it echoes. If the configuration is kept in the browser's own serialization, "is this origin allowed?" is set membership, and the classic mistakes (prefix tests, suffix tests, case folding) have nowhere to happen. Patterns are the one place where a real match is needed, and they are checked with an anchored prefix, an anchored suffix and a strict test of what lies between.

Credentials and the wildcard look like two features, but they are one decision. A response that `*` makes readable by everyone must be the same for every user, so it never carries credentials; a response that carries credentials must name exactly one origin and must tell caches that it varies with `Origin`. Writing that decision once and deriving the three headers from it keeps them consistent.

### Algorithm

1. `originOf`: split off the scheme at the first `:`, check its form and that it has a default port, require `//`, cut the authority at the first `/`, `?` or `#`, drop everything up to the last `@`, split host and port at the first `:`, check both, lowercase, and drop the default port.
2. `allowOrigin`: store the serialization in a set, except an opaque origin that was not written as the literal `null`.
3. Decision (`allowOriginFor`): any origin and no credentials gives `*`; a listed origin gives itself; any origin gives `*`; otherwise `""`. Listed means in the set, or matched by a pattern.
4. `needsPreflight`: normalize the method; a method other than `GET`, `HEAD`, `POST` needs a preflight. Otherwise check each row with the safelist function and sum the values; any unsafe row, or a sum above 1024, needs one.
5. `preflightResponse`: decide the origin; check the method (safelisted, listed, or `*` when the answer has no credentials) and every requested name (listed, or `*` under the same condition and not `authorization`); return `[]` on any failure, else the rows in their fixed order.
6. `actualResponse`: the decision, then `Access-Control-Allow-Credentials` when credentials are on and the value is the origin itself, then `Vary: Origin` unless the policy is "any origin, no credentials".
7. `allowPattern`: parse with one anchored expression, normalize, and keep the prefix `scheme://` and the suffix `.host:port`. A match is an origin with that prefix and suffix and one or more dotted lowercase labels between.
8. `lint`: one row per broad pattern, one for `null` in the set, and, with credentials, one per origin or pattern whose scheme is not `https` or `wss`; sort.

### Correctness

Origins: each step of the statement's reading is one step of the algorithm, in the same order, and each failure returns `null`, so the serialization is the statement's. Two URLs with the same scheme, host and port serialize to the same text and two with any part different do not, so set membership is exactly "same origin".

Decision: the four rules are tested in the stated order and each returns, so exactly one applies. `Access-Control-Allow-Credentials` is added only when the value equals the request's own origin and is not `*` or empty, which is the condition the browser's CORS check needs for a credentialed request and the only one in which credentials are safe to grant. `Vary` is omitted only under rule 1, where the decision does not read `Origin`, so every response whose headers depend on `Origin` carries it.

Preflight: each of the three checks is necessary for the browser to allow the real request, and the answer is built only after all three pass, so a refused preflight carries no CORS headers at all. The wildcards are honored only when the answer has no credentials header, which is when the browser honors them too.

Patterns: the prefix and suffix are anchored at the two ends of the origin, and the middle must be non-empty dotted labels without `:`, `/` or `@`, so a match is exactly a subdomain at any depth of the pattern's host, with the same scheme and port. The apex host fails because the middle would be empty, `evilshop.example` fails because the suffix starts with a dot, and `shop.example.other.test` fails because it does not end with the suffix.

### Complexity

- Time: O(P L) per request — a set lookup in O(L), then at most one prefix and suffix comparison per pattern; the safelist check is linear in the values, and `lint` sorts at most `C` rows.
- Space: O(C) — the set of origins, the patterns with their precomputed prefix and suffix, and the lists of methods and headers.

### Trade-offs

- Exact lookups make the common case trivial and safe, at the cost of requiring every allowed origin to be listed. Patterns trade that for convenience, and every pattern is a promise about all the subdomains that exist now or later.
- Answering a refused preflight with no headers tells a prober nothing about the policy. A static answer that always lists the allowed methods and headers is simpler to cache in front of the server, and the browser still enforces it; the Fetch standard allows both.
- Echoing the origin with `Vary: Origin` costs cache hit rate: a shared cache keeps one copy per origin. A truly public resource is better served with a static `*`, which needs no `Vary`.
- The linter's rules are syntactic. They cannot know that `*.co.uk` is a public suffix or that one subdomain hosts user content, so a clean report is a floor, not a proof.

### Pitfalls and edge cases

- **Default ports and case.** `https://x.example:0443` is `https://x.example`, `http://x.example:443` keeps its port, `ws` and `ftp` have defaults too, and an empty port is the default (`h2`). Scheme and host are lowercased, the trailing dot of a host is kept (`h4`).
- **User information.** The host is after the *last* `@` of the authority, so `https://app.example@files.example` is `files.example` (`h1`). An `@` in the path does not count.
- **Not a URL.** No `//`, an empty host, a space, a port above 65535 or with letters, a scheme starting with a digit: all `null` (`h3`).
- **Normalizing the request.** Lowercasing or trimming `Origin` before the lookup, or matching it as a prefix or suffix, accepts origins the browser never sent or other sites' origins (`h5`).
- **Configuring `null` by accident.** A `file:` URL, `*` or a bare host in the allow-list has no origin of its own and must be refused, or it silently allows every opaque origin (`h6`).
- **Method case.** `get` is normalized before the safelist check (`ex3`, `h11`), but the server compares `patch` and `PATCH` exactly (`h12`, `h14`).
- **The safelist.** `content-type`'s essence ignores case and spaces around it but the value must have no unsafe character (`h8`); two `content-type` rows are checked one by one; `range` needs a start and an ordered pair (`h9`); the limits are "more than 128" and "more than 1024" (`h10`); a tab is not unsafe (`h11`).
- **Safelisted names on the server.** `content-type` in `Access-Control-Request-Headers` must be allowed explicitly (`h12`), and names are compared without case after trimming (`h13`).
- **Partial answers.** Sending `Access-Control-Allow-Origin` for a preflight whose method or headers are not allowed hides nothing and gains nothing (`ex4`).
- **`*` with credentials.** Sending `*` together with `Access-Control-Allow-Credentials: true` fails the browser's CORS check for any request with credentials; "fixing" it by echoing any origin with credentials hands every user's data to every site (`h17`). Only listed origins get credentials.
- **`Vary`.** It belongs on refusals too (`h16`), and not on a static `*` (`ex6`, `h18`). An allow-listed origin under "any origin, no credentials" still gets `*` (`h18`).
- **Method and header wildcards.** They do not cover `authorization` (`h19`) and do not count when the answer allows credentials (`h20`).
- **An empty `Origin`.** It is never listed, so it never gets credentials (`h21`).
- **Pattern matching.** Anchor both ends; require at least one label in front; compare the port (`ex7`, `h23`, `h25`).
- **Pattern parsing.** Normalize like an origin, and refuse anything that is not exactly `scheme://*.host[:port]` (`h22`).
- **The linter.** `null` is reported with or without credentials, insecure schemes only with credentials, `wss` counts as secure and `ws` and `ftp` do not, and only a single-label host is broad (`h25` to `h28`).

### Language notes

- Python: `str.partition` and `str.rpartition` split at the first and last separator, which is exactly the "first `:`" and "last `@`" of the statement. `re.fullmatch` anchors both ends. Lists of two strings sort lexicographically, so `sorted(findings)` is the linter's order.
- TypeScript: `indexOf` and `lastIndexOf` play the same roles; regular expressions need `^` and `$` to be anchored. `Set` and `Map` keep the configuration free of inherited keys, and an array keeps the methods and headers in the order they were added. Strings compare by UTF-16 code units with `<`, which for ASCII is the order of character codes.

## Further reading

- [Fetch Standard, 3.3 CORS protocol](https://fetch.spec.whatwg.org/#http-cors-protocol): the request and response headers, the table of credentials and wildcard combinations, `*` for methods and headers only without credentials, and the note on `Vary` under "CORS protocol and HTTP caches".
- [Fetch Standard, 4.10 CORS check](https://fetch.spec.whatwg.org/#cors-check) and [4.9 CORS-preflight fetch](https://fetch.spec.whatwg.org/#cors-preflight-fetch): how a browser decides, byte for byte, whether a response may be shared and whether a preflight allows a request.
- [Fetch Standard, 2.2.1 Methods and 2.2.2 Headers](https://fetch.spec.whatwg.org/#methods): CORS-safelisted methods, method normalization, CORS-safelisted request-headers, the unsafe bytes and the 128 and 1024 limits, and `Authorization` as the non-wildcard header name.
- [RFC 6454, The Web Origin Concept](https://www.rfc-editor.org/rfc/rfc6454): the origin of a URI as scheme, host and port, comparison, and serialization without the default port.
- [URL Standard, origin](https://url.spec.whatwg.org/#origin) and [special schemes](https://url.spec.whatwg.org/#special-scheme): which schemes have a tuple origin and their default ports.
- [HTML Standard, origin](https://html.spec.whatwg.org/multipage/browsers.html#origin): the serialization of an origin, and `null` for an opaque one.
- [RFC 9110, HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110), sections 9.3.7 (OPTIONS responses are not cacheable) and 12.5.5 (`Vary`).
- [OWASP HTML5 Security Cheat Sheet, Cross Origin Resource Sharing](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html#cross-origin-resource-sharing): allow only selected, trusted origins, keep `*` off sensitive responses, never echo `Origin` blindly, and keep access control on requests that get no preflight.
