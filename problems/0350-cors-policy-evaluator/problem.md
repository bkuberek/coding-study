# CORS Policy Evaluator

## Statement

Build `CorsPolicy`, the part of a web API that decides which other websites may read its responses from a browser, and writes the response headers that say so. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**Why this exists.** A browser keeps the pages of different sites apart. A page from `https://news.example` may *send* a request to `https://bank.example`, but it may not *read* the answer, because the browser would attach the user's cookies for the bank, and the bank's answer would then show the user's private data to a page the bank does not know. This rule is the **same-origin policy**. Sometimes a server does want another site to read its answers, for example an API at `https://api.shop.example` used by the shop's own front end at `https://shop.example`. **Cross-Origin Resource Sharing** (CORS) is how the server says so: the browser tells the server where the page came from in an `Origin` request header, and the server answers with headers such as `Access-Control-Allow-Origin`. The browser compares them and only then hands the response to the page. The server decides; the browser enforces.

A mistake in that decision is a security bug that is easy to miss, because the site still works for the people it should work for. It also works for a site it should not.

Aim to finish in 90 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 30, level 2 by 55, level 3 by 70 and level 4 by 85, keeping the last minutes for a final run.

## Input

- `CorsPolicy()`: creates an empty policy, which allows no origin.
- Every argument is ASCII text without control characters, except the header values given to `needsPreflight`, which may hold any ASCII character.
- Each level's section describes the methods it adds and their parameters.

## Output

- Response headers come back as rows `[name, value]`, in the order the level that adds them states, `[]` when there are none. Header names are written exactly as given in the statement, for example `Access-Control-Allow-Origin`.
- A method that returns text returns `""` for "nothing".

## Level 1: Origins and an allow-list

**What an origin is.** An origin is where a page comes from, as a triple of **scheme**, **host** and **port** (RFC 6454). `https://shop.example/cart?id=7` has the origin (`https`, `shop.example`, 443): the path and the query do not matter, and 443 is the port `https` uses when none is written. Two URLs have the same origin only when all three parts are equal, so `http://shop.example` (another scheme), `https://shop.example:8443` (another port) and `https://api.shop.example` (another host) are three different origins. Some URLs have no origin of this kind, for example a `data:` URL or a local file. Their origin is **opaque** and is written as `null`.

An origin is written (serialized) as `scheme://host`, followed by `:port` only when the port is not the scheme's default. That text, with no path and no trailing slash, is what a browser sends in the `Origin` header.

- `originOf(url)`: the serialized origin of `url`, or `"null"` when its origin is opaque. In this problem a URL is read like this:
  1. The **scheme** is the text before the first `:`. It must start with an ASCII letter followed by letters, digits, `+`, `-` or `.`, and is compared in lowercase.
  2. Only these schemes have a scheme-host-port origin, with these default ports: `http` 80, `https` 443, `ws` 80, `wss` 443, `ftp` 21. Any other scheme gives `null`.
  3. The scheme's `:` must be followed by `//`. The **authority** is the text after `//` up to the first `/`, `?` or `#`, or to the end.
  4. If the authority holds an `@`, everything up to and including the *last* `@` is user information, which is not part of the origin.
  5. The rest is the host, then optionally `:` and a port. The **host** is one or more ASCII letters, digits, `-` and `.`, lowercased. The **port** is zero or more digits: none means the default, otherwise its value counts (so `0443` is 443) and must be at most 65535.
  6. Anything else (a missing piece, another character in the host, a port that is not a number or too large) gives `null`.
- `allowOrigin(url)`: adds the origin of `url` to the allow-list and returns its serialization. The literal text `null` adds the opaque origin `null` and returns `"null"`. Any other text whose origin is opaque adds nothing and returns `""`. Adding an origin that is already allowed changes nothing and returns it again.
- `allowOriginFor(origin)`: `origin` is the value of a request's `Origin` header. Returns the value for the response's `Access-Control-Allow-Origin` header: `origin` itself when it is exactly, character for character, an origin of the allow-list, else `""` (no header, so the browser will not share the response).

The comparison is exact because the browser's check is exact: it compares `Access-Control-Allow-Origin` with its own serialization of the page's origin, byte for byte. The header is not parsed or normalized here: a browser always sends a serialized origin, so a value such as `https://App.example` or `https://app.example/` does not come from one.

### Example 1

<!-- case: ex1 -->

The path, the query and the default port 443 are not part of the origin, and the scheme and the host are lowercased. Port 8080 is not the default for `http`, so it stays. A `data:` URL has an opaque origin.

### Example 2

<!-- case: ex2 -->

The allow-list holds `https://app.example` and `https://admin.app.example:8443`, written from URLs with a path. A request from `http://app.example` (another scheme) or from `https://app.example:8443` (another port) is another origin and gets no header. The last request's `Origin` has a trailing slash, which no serialized origin has.

## Level 2: Preflight requests

Not every cross-origin request is sent right away. A request that a plain HTML form could also send (a *simple* request: method `GET`, `HEAD` or `POST`, with only a few harmless headers) goes out directly, and CORS only decides whether the page may read the answer. Any other request, such as a `PUT` or a `POST` with a JSON body, could change data on a server that never heard of CORS. So the browser first asks permission with a **preflight**: an `OPTIONS` request that carries the `Origin`, the method it wants in `Access-Control-Request-Method`, and the names of the extra headers in `Access-Control-Request-Headers`. The real request is sent only if the answer allows all of it.

- `allowMethod(method)`: allows `method`. Methods are case-sensitive: `PATCH` and `patch` are different. Returns `true` when it was not allowed yet, else `false`.
- `allowHeader(name)`: allows the request header `name`. Header names are case-insensitive and are kept in lowercase. Returns `true` when it was not allowed yet (in any case), else `false`.
- `setMaxAge(seconds)`: how long a browser may cache the answer to a preflight. Until it is called, no `Access-Control-Max-Age` header is sent (browsers then cache for 5 seconds). A later call replaces the value.
- `needsPreflight(method, headers)`: the browser's side. `method` is the method as the page wrote it, and `headers` the request headers it set, as rows `[name, value]`. Returns `true` when the browser must send a preflight first, following the Fetch standard:
  1. **Normalize** the method: if it is `DELETE`, `GET`, `HEAD`, `OPTIONS`, `POST` or `PUT` in any case, uppercase it. Any other method stays as written (`patch` stays `patch`).
  2. If the method is not exactly `GET`, `HEAD` or `POST`, return `true`.
  3. Each header row is checked on its own. A header is **safelisted** when its value has at most 128 characters and its name, in any case, is one of:
     - `accept`, and the value has no *unsafe* character.
     - `accept-language` or `content-language`, and every character of the value is an ASCII letter, a digit, a space or one of `*` `,` `-` `.` `;` `=`.
     - `content-type`, the value has no unsafe character, and its *essence* is `application/x-www-form-urlencoded`, `multipart/form-data` or `text/plain`. The essence is the part before the first `;`, without leading or trailing spaces and tabs, compared in lowercase.
     - `range`, and the value is `bytes=`, one or more digits, `-`, then zero or more digits; when the second number is there, it is not smaller than the first.

     The *unsafe* characters are those below code 32 except the tab, the character with code 127, and `"` `(` `)` `:` `<` `>` `?` `@` `[` `\` `]` `{` `}`.
  4. Return `true` if any header is not safelisted, or if the values of all the headers add up to more than 1024 characters. Otherwise return `false`.
- `preflightResponse(origin, method, requestHeaders)`: the server's answer to a preflight with these three request headers. `method` is compared exactly as sent. `requestHeaders` is a comma-separated list of names, `""` when the header is absent; split it on `,`, remove spaces and tabs around each name, skip empty names, and compare in lowercase. Answer with headers only when everything is allowed:
  1. The origin must be allowed, as for `allowOriginFor`.
  2. The method must be `GET`, `HEAD` or `POST` (which the browser always allows), or an allowed method.
  3. Every requested header name must be allowed. There is no exception for safelisted names: the browser lists a name only when that header is not safelisted, as `content-type` is when its value is `application/json`.

  If any of these fails, return `[]`: the browser then refuses the real request, and the server has told it nothing about its policy. Otherwise return these rows, in this order, each only when it applies:
  - `Access-Control-Allow-Origin`: the value of `allowOriginFor(origin)`.
  - `Access-Control-Allow-Methods`: every allowed method, in the order they were allowed, joined with `", "`, when at least one is.
  - `Access-Control-Allow-Headers`: every allowed header name, in lowercase and in the order they were allowed, joined with `", "`, when at least one is.
  - `Access-Control-Max-Age`: the seconds, in decimal, once `setMaxAge` was called.

  HTTP defines responses to `OPTIONS` as not cacheable, so the preflight answer has no `Vary` header, even though it depends on the origin.

### Example 1

<!-- case: ex3 -->

A `GET` without extra headers is simple. A `POST` with a `text/plain` body is too, even with a parameter after `;`. A JSON body, a `PUT`, or an `Authorization` header each need a preflight. `get` is normalized to `GET`, and `Accept: text/html` is safelisted.

### Example 2

<!-- case: ex4 -->

The policy allows `PUT` and `DELETE`, two headers and a cache time of 600 seconds. The first preflight asks for `PUT` with both headers and gets the full answer. `PATCH` is not allowed, `authorization` is not an allowed header, and `https://other.example` is not an allowed origin, so each of those gets no headers at all.

## Level 3: Credentials and the wildcard

A request carries **credentials** (cookies, or HTTP authentication) only when the page asks for them. With credentials, the browser shares the response only when `Access-Control-Allow-Origin` names the page's origin exactly *and* the response also has `Access-Control-Allow-Credentials: true`. The wildcard `*` in `Access-Control-Allow-Origin` means "any origin may read this", and the browser accepts it only for requests *without* credentials. That combination is deliberate: a response that any site may read must not depend on who the user is.

- `allowAnyOrigin()`: allows every origin, through the wildcard.
- `allowCredentials()`: allows credentials for the origins that are allowed by name.
- `actualResponse(origin)`: the CORS headers for the response to a real (not preflight) request with this `Origin`. A server cannot always tell whether the page asked for credentials (a request that asked but has no cookie to send looks the same as one that did not ask), so the answer depends on the policy alone.

The decision about the origin, which `allowOriginFor` returns from now on:

1. Any origin allowed and credentials not allowed: `*`, for every origin, also for those on the allow-list. The response is the same for everyone.
2. Otherwise, an origin of the allow-list gets itself.
3. Otherwise, with any origin allowed, `*`.
4. Otherwise `""`.

The rows of `actualResponse`, in this order, each only when it applies:

- `Access-Control-Allow-Origin`: the value decided above, unless it is `""`.
- `Access-Control-Allow-Credentials: true`: when credentials are allowed and the value is the request's own origin. Never next to `*`.
- `Vary: Origin`: whenever the response depends on the `Origin`, which is every case except rule 1. This includes a response with no `Access-Control-Allow-Origin` at all.

`Vary` tells HTTP caches (the browser's own, and any in between) that the response was chosen by the `Origin` request header, so a cached copy made for one origin is not served to another. Without it, an answer made for a request with no `Origin`, or from a refused origin, could be cached without `Access-Control-Allow-Origin` and then served to an allowed origin, and the other way round. With rule 1 the response is the same for everyone and needs no `Vary`.

`preflightResponse` follows the same decision for its `Access-Control-Allow-Origin` row, and adds `Access-Control-Allow-Credentials: true` right after it under the same condition. The **wildcard** also exists for methods and headers: an allowed method `*` allows any method, and an allowed header `*` allows any header name except `authorization`, which must always be allowed by name. A browser treats them as wildcards only for a request without credentials. A preflight never carries credentials, so the server cannot know whether the real request will; when its answer allows credentials, it answers as the browser will judge a request that has them. So both wildcards count only when the answer does not allow credentials; next to `Access-Control-Allow-Credentials: true`, `*` is just a name that matches only itself. `*` is still listed in `Access-Control-Allow-Methods` and `Access-Control-Allow-Headers` like any other entry.

### Example 1

<!-- case: ex5 -->

`https://app.example` may send credentials: its response names it and adds `Access-Control-Allow-Credentials`. The refused origin still gets `Vary: Origin`. The preflight answer allows credentials as well, so the browser may send the real `PUT` with cookies.

### Example 2

<!-- case: ex6 -->

With any origin allowed and no credentials, every response says `*`, also to an opaque `null` origin, and no `Vary` is needed. Once credentials are allowed too, `*` is still the answer for an origin that is not on the allow-list, which a browser accepts only for a request without credentials, and the response now depends on the origin, so `Vary: Origin` is added.

## Level 4: Patterns, the null origin and a linter

An API used by many subdomains (`eu.shop.example`, `us.shop.example`, ...) is often configured with a pattern instead of a list. Patterns are where many real CORS bugs live: a check that the origin "ends with `shop.example`" also accepts `https://evilshop.example`, and a check that it "starts with `https://shop.example`" also accepts `https://shop.example.other.test`.

- `allowPattern(pattern)`: allows every origin that `pattern` matches. A pattern is exactly `scheme://*.host`, optionally followed by `:port`, with nothing before or after: a scheme from the list of level 1, then `://*.`, then a host of one or more labels separated by single dots (a label is one or more ASCII letters, digits and `-`), then optionally `:` and one or more digits, at most 65535. Scheme and host are kept in lowercase and a default port is dropped, as for an origin, so `HTTPS://*.Shop.Example:443` is `https://*.shop.example`. Returns `true` when the pattern is valid and was not allowed yet, else `false`, and an invalid pattern changes nothing.
- A pattern **matches** an `Origin` value that is exactly `scheme://`, then one or more labels of lowercase ASCII letters, digits and `-` separated by single dots, then `.host`, then the pattern's `:port` when it has one, and nothing more. So `https://*.shop.example` matches `https://eu.shop.example` and `https://a.b.shop.example`, but not `https://shop.example` itself, not `https://evilshop.example`, not `http://eu.shop.example` and not `https://eu.shop.example:8443`. An origin matched by a pattern counts as on the allow-list in every rule of the earlier levels.

**The null origin.** A browser sends `Origin: null` from any page whose origin is opaque, such as a page loaded from a `data:` URL, a frame sandboxed into an opaque origin or, in many browsers, a local file, and also for some requests that were redirected across origins. Anyone can create such a page, so allowing `null` allows everyone, and with credentials it hands the user's data to anyone. A pattern never matches `null`.

- `lint()`: reports the risky parts of the policy as rows `[code, subject]`, sorted by code and then by subject (by character codes), `[]` when there are none:
  - `broad-pattern`, with the pattern as subject: a pattern whose host is a single label, such as `https://*.com`, which matches every site under that name.
  - `credentials-to-insecure-origin`, with the origin or the pattern as subject: while credentials are allowed, an allow-list origin (other than `null`) or a pattern whose scheme is not `https` or `wss`. A page from a plain `http` origin can be changed by anyone on the network path, so with credentials allowed they could read the user's data through it.
  - `null-origin-allowed`, with subject `null`: the opaque origin is on the allow-list.

### Example 1

<!-- case: ex7 -->

`https://*.example.com` matches one subdomain or several, but not the name itself, not a name that only ends with the same letters, not a name that has `example.com` in the middle, and not another scheme.

### Example 2

<!-- case: ex8 -->

The policy allows `null`, a plain `http` origin and a pattern over a single label, and it allows credentials, so `lint` reports all three, sorted by code.

## Constraints

- At most 200 calls per test.
- Every text argument has at most 300 characters, and `headers` has at most 20 rows.
- `seconds` is from 0 to 86400.
- No URL, origin or pattern uses a host in square brackets (an IPv6 address). The digits in a `range` value are at most 15 per number.

## Follow-ups

- Real URL parsers accept much more than this problem's grammar: backslashes, missing slashes, percent-encoded and international hosts. Why does a server never need to parse the `Origin` header to answer correctly, and what does it need to parse instead?
- The `broad-pattern` rule only sees one label. A pattern over `co.uk` is just as broad. What data would you need to catch that, and where would it come from?
- Private network access: a page on the public internet sending requests to a device on the user's home network. Which extra preflight would protect that device, and who would have to answer it?
- Your API allows credentials for `https://*.shop.example`. One subdomain hosts user-uploaded pages. What does that do to the policy, and how would you narrow it?

## Hints

### Hint 1

Start with `originOf` and do it in small steps, each one able to give up with `"null"`: find the scheme, check the `//`, cut the authority at the first `/`, `?` or `#`, cut off the user information at the last `@`, then split host and port. Write each step as it is listed in the statement; the order matters.

### Hint 2

Keep the allow-list as a set of serialized origins. Because `allowOrigin` serializes its input and the browser sends serialized origins, deciding is one exact lookup: no lowercasing, trimming or prefix test of the request's `Origin`.

### Hint 3

For `needsPreflight`, write one function that decides whether a single `[name, value]` row is safelisted, with one branch per header name, and a helper for the unsafe characters. Then a loop over the rows that also adds up the value lengths. Check the limits at the exact boundary: 128 characters is still fine, and so is a total of exactly 1024.

### Hint 4

For `preflightResponse`, first decide the origin, then check the method and every requested name, and only then build the rows. Returning `[]` early on the first failure keeps the order of the rows easy to get right.

### Hint 5

Level 3 is one decision used in three places (`allowOriginFor`, `actualResponse` and `preflightResponse`). Write it once, as the four ordered rules, and derive from it both whether credentials may be allowed in this answer and whether `Vary` is needed. The method and header wildcards then depend on "does this answer allow credentials?".

### Hint 6

A pattern matches when the origin starts with `scheme://`, ends with `.host` plus the port part, and what is left in between is one or more non-empty labels separated by single dots. Precompute that prefix and suffix when the pattern is added. For the linter, collect the rows from the patterns and the allow-list, then sort them once by code and subject.
