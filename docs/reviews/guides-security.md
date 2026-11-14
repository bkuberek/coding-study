# Review: the facts of the security guides

The seven guides of the path "Security: from trust boundaries to certificate chains and threat models" ([guides](../specs/guides.md), [ADR 0025](../decisions/0025-concept-guides-and-learning-paths.md)) state facts about OWASP cheat sheets and rankings, WHATWG standards, RFCs, NIST publications, a paper, an open standard for access control policies and Python's standard library. This page lists each one with where it was checked, so that the independent review starts from the sources.

"Quote" means the exact text was read at that source: on the web page, or in the raw file fetched from the project's repository at the tag named. "Run" means an example of the guide, or a one-off program, printed it, on CPython 3.13.12. "Arithmetic" means the number was computed from the stated inputs. The guides state only facts checked one of these ways; the last sections list the citation choices, what the guides do not state for lack of a source, and where a guide comes close to a linked problem.

| Guide | Slug |
|-------|------|
| Trust boundaries and injection | `trust-boundaries-and-injection` |
| Output encoding by context | `output-encoding` |
| Same-origin policy and CORS | `same-origin-and-cors` |
| Authentication, authorization and policy engines | `authentication-and-authorization` |
| Secrets and redaction | `secrets-and-redaction` |
| TLS, certificates and chain validation | `tls-and-certificates` |
| Threat modeling | `threat-modeling` |

## OWASP Top 10:2025

The current edition, at [top10.owasp.org/2025](https://top10.owasp.org/2025) (owasp.org/Top10/2025 redirects there). Used in `trust-boundaries-and-injection`, `authentication-and-authorization` and `threat-modeling`.

| # | Claim | Source |
|---|-------|--------|
| T1 | The ten categories, in order: A01 Broken Access Control, A02 Security Misconfiguration, A03 Software Supply Chain Failures, A04 Cryptographic Failures, A05 Injection, A06 Insecure Design, A07 Authentication Failures, A08 Software or Data Integrity Failures, A09 Security Logging and Alerting Failures, A10 Mishandling of Exceptional Conditions | Quote: [Top 10:2025](https://top10.owasp.org/2025) |
| T2 | A05: an application flaw that lets untrusted user input be sent to an interpreter and causes the interpreter to execute parts of that input as commands; it includes cross-site scripting and SQL injection; the preferred prevention is a safe API that avoids the interpreter or provides a parameterized interface, with positive server-side validation, and escaping only for residual dynamic queries | Quote: [A05:2025 Injection](https://top10.owasp.org/2025/A05_2025-Injection/) |
| T3 | A01: access control keeps users from acting outside their intended permissions; "Except for public resources, deny by default"; viewing or editing someone else's account by providing its identifier; CORS misconfiguration; CWE-918, server-side request forgery, is among its mapped CWEs | Quote: [A01:2025 Broken Access Control](https://top10.owasp.org/2025/A01_2025-Broken_Access_Control/) |

## Injection and input validation

OWASP cheat sheets, read at cheatsheetseries.owasp.org, and the OWASP community page on path traversal. Used in `trust-boundaries-and-injection`.

| # | Claim | Source |
|---|-------|--------|
| I1 | SQL injection: untrusted data becomes part of a query's SQL syntax; the preferred patterns are parameterized queries for data and an allowlist of fixed, application-owned values for structure; parameter markers represent data values, not table names, column names or `ASC` and `DESC`; manual escaping is strongly discouraged | Quote: [SQL Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html), *Introduction*, *Primary Defenses*, *Allow-List Input Validation*, *Manually escaping (STRONGLY DISCOURAGED)* |
| I2 | Binding a stored procedure's arguments protects the call, not dynamic SQL built inside the procedure | Quote: same, *SQL Injection inside stored Procedures and Functions* |
| I3 | Least privilege as hardening, to limit the damage of a successful injection; no DBA or administrator access for application accounts | Quote: same, *Hardening*, *Least Privilege* |
| I4 | The controls apply whether data comes from an HTTP request, another service or previously stored data | Quote: same, *Resolution* |
| I5 | Validate both syntax and semantics; do not try to recognize every malicious string; validate on the server, since client-side validation is bypassable; parameterized queries for SQL and context-aware output encoding for XSS | Quote: [Input Validation Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html), *Introduction*, *Input Validation Strategies*, *Common Pitfalls* |
| I6 | Validate data from internal APIs, partner feeds, queues and stored records when it crosses a trust boundary; "An internal transport does not establish that a value meets the receiving component's rules" | Quote: same, *Common Pitfalls* |
| I7 | Decode according to the protocol before checking field rules; where a field needs Unicode normalization, apply one policy before validation, storage and comparison; normalization is not sanitization and does not replace output encoding | Quote: same, *Validating Free-form Unicode Text* |
| I8 | Command injection: the primary defense is to avoid calling OS commands directly; separate the program from its arguments, as a list; every OS command injection is also an argument injection; `--` ends option parsing for commands that support it | Quote: [OS Command Injection Defense Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/OS_Command_Injection_Defense_Cheat_Sheet.html), *Defense Option 1*, *Argument Injection*, *Layer 2*, code examples |
| I9 | Path traversal reaches files and directories outside the web root; `%2e%2e%2f` represents `../` | Quote: [OWASP, Path Traversal](https://community.owasp.org/attacks/Path_Traversal) |

## Cross-site scripting and output encoding

Used in `output-encoding`, and X9 in `same-origin-and-cors` too.

| # | Claim | Source |
|---|-------|--------|
| X1 | Output encoding as close as possible to where the data is rendered; the five replacements `&` to `&amp;`, `<` to `&lt;`, `>` to `&gt;`, `"` to `&quot;`, `'` to `&#x27;` | Quote: [Cross Site Scripting Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html) |
| X2 | Always surround attribute values with quotes, in bold; in an unquoted value, whitespace ends it | Quote: same |
| X3 | "HTML attribute encoding alone does not protect JavaScript in an event-handler attribute", "URL-bearing attributes require URL validation", "There is no universally safe list of HTML attributes"; allowlist `http` and `https` URLs | Quote: same |
| X4 | Many frameworks escape every value they render by default, and escape hatches bring the risk back; user-authored HTML needs a maintained sanitizer; modifying sanitized content afterwards can void it | Quote: same |
| X5 | Encode parameter values, not the entire URL | Quote: same |
| X6 | Dangerous contexts even with encoding: directly in a script, inside an HTML comment, callback functions; `eval()`, `setInterval()`, `setTimeout()` | Quote: same |
| X7 | CSP as an additional layer, not the primary defense; sent as the `Content-Security-Policy` response header, it lets the browser block inline and remote scripts; it should not be the only defense against XSS | Quote: XSS cheat sheet; [Content Security Policy Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html) |
| X8 | Stored, reflected and DOM-based XSS; server XSS and client XSS; DOM-based XSS is a subset of client XSS | Quote: [OWASP, Types of Cross-Site Scripting](https://community.owasp.org/Types_of_Cross-Site_Scripting) |
| X9 | XSS can defeat all CSRF mitigation techniques | Quote: [Cross-Site Request Forgery Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html), *Introduction* |

## HTML Standard

The WHATWG HTML Standard, multipage edition. Used in `output-encoding` (H1 to H6) and `same-origin-and-cors` (H7, H8).

| # | Claim | Source |
|---|-------|--------|
| H1 | Data state: `&` switches to the character reference state, `<` to the tag open state | Quote: [13.2.5.1 Data state](https://html.spec.whatwg.org/multipage/parsing.html#data-state) |
| H2 | Double-quoted attribute value state: `"` switches to the after attribute value (quoted) state, `&` to the character reference state; unquoted attribute value state: tab, line feed, form feed and space switch to the before attribute name state, `>` emits the tag | Quote: 13.2.5.36 and 13.2.5.38 |
| H3 | Script data state and RAWTEXT state have no rule for `&`, only for `<`; a `script` start tag switches the tokenizer to the script data state; `style` follows the generic raw text element parsing algorithm, which switches to the RAWTEXT state | Quote: 13.2.5.3, 13.2.5.4, 13.2.6.2 and the "in head" insertion mode |
| H4 | Escape `<!--`, `<script` and `</script` in script literals as `\x3C!--`, `\x3Cscript` and `\x3C/script`; for legacy reasons `<!--` and `<script` must be balanced for the parser to close the block | Quote: [Restrictions for contents of script elements](https://html.spec.whatwg.org/multipage/scripting.html#restrictions-for-contents-of-script-elements) |
| H5 | A script whose type is not a JavaScript type is a data block, not processed by the user agent; its data must be inline and its format given by `type` | Quote: [the script element](https://html.spec.whatwg.org/multipage/scripting.html#the-script-element) |
| H6 | The image loading algorithm fires an event named `error` at the element; the guide only calls `onerror` a handler for that event | Quote: [images, update the image data](https://html.spec.whatwg.org/multipage/images.html), step 12.2 |
| H7 | Origins are the fundamental currency of the web's security model; two actors sharing an origin are assumed to trust each other and to have the same authority; an opaque origin serializes as `null`; the port is appended only when non-null; a site is an opaque origin or a scheme and host; `https://example.com` and `https://sub.example.com` are same site | Quote: [Origins](https://html.spec.whatwg.org/multipage/browsers.html#origin) |
| H8 | The sandboxed origin browsing context flag forces content into an opaque origin, unless `allow-same-origin` is given | Quote: same page, sandboxing |

## URLs and JSON

Used in `output-encoding`.

| # | Claim | Source |
|---|-------|--------|
| U1 | Producers should use uppercase hexadecimal digits in percent-encodings; the unreserved characters are ALPHA, DIGIT, `-`, `.`, `_`, `~`; implementations must not percent-encode or decode the same string more than once; data is first encoded as UTF-8; the query ends at `#`; the fragment is separated before a dereference and dereferenced solely by the user agent | Quote: [RFC 3986](https://www.rfc-editor.org/rfc/rfc3986), sections 2.1, 2.3, 2.4, 2.5, 3.4 and 3.5 |
| U2 | Form-urlencoded parsing splits on `&`, takes the name up to the first `=`, and replaces `+` with a space in name and value | Quote: [URL Standard, 5.1](https://url.spec.whatwg.org/#urlencoded-parsing) |
| U3 | Any character may be escaped in a JSON string; `\uXXXX` for a character in the Basic Multilingual Plane | Quote: [RFC 8259](https://www.rfc-editor.org/rfc/rfc8259), section 7 |

## Same-origin policy and CORS

RFC 6454; the WHATWG Fetch Standard; OWASP cheat sheets. Used in `same-origin-and-cors`.

| # | Claim | Source |
|---|-------|--------|
| C1 | Two URIs are same-origin when they have the same scheme, host and port; origins are the same only if identical; the serialization omits the default port; a URI without a hierarchical naming authority gets a fresh globally unique identifier; the `Origin` header may be `null`, and a privacy-sensitive context must send `null` | Quote: [RFC 6454](https://www.rfc-editor.org/rfc/rfc6454), sections 3.2, 4, 5, 6.2, 7 and 7.3 |
| C2 | Reading information from another origin is generally forbidden; sending information to another origin is permitted | Quote: RFC 6454, section 3.4.2 |
| C3 | CORS-safelisted methods are `GET`, `HEAD` and `POST`; safelisted request headers are `accept`, `accept-language`, `content-language`, `content-type` and `range`; `content-type` essences `application/x-www-form-urlencoded`, `multipart/form-data`, `text/plain`; a value longer than 128 is not safelisted; the CORS-unsafe request-header bytes; safelisted values over 1024 in total add their names to the unsafe names | Quote: [Fetch Standard](https://fetch.spec.whatwg.org/), 2.2.1 and 2.2.2 |
| C4 | CORS lets responses declare they can be shared; it must be opt-in to keep data in responses behind a firewall (intranets) from leaking; a CORS request includes `Origin`; a CORS-preflight request uses `OPTIONS` with `Access-Control-Request-Method` and `Access-Control-Request-Headers` | Quote: Fetch, 3.3 |
| C5 | The meanings of `Access-Control-Allow-Origin` (the literal value of `Origin`, or `null`, or `*`), `-Allow-Credentials`, `-Allow-Methods`, `-Allow-Headers`, `-Max-Age` (5 seconds by default) and `-Expose-Headers` | Quote: Fetch, 3.3 |
| C6 | With credentials mode `include`, `Access-Control-Allow-Origin` cannot be `*`; `true` is byte case-sensitive; `*` counts as a wildcard for methods, headers and exposed headers only for requests without credentials; `Authorization` is the CORS non-wildcard request-header name; sharing responses and allowing credentials together is rather unsafe; a preflight never includes credentials | Quote: Fetch, 2.2.2 and 3.3 |
| C7 | The CORS check: no `Access-Control-Allow-Origin` fails; `*` succeeds without credentials; a value other than the serialized request origin fails; without credentials success; otherwise `Access-Control-Allow-Credentials` must be `true` | Quote: Fetch, CORS check; run: `cors_check.py` |
| C8 | The CORS-preflight fetch runs the CORS check on the original request rather than the preflight, to use the right credentials mode | Quote: Fetch, 4.8, step 7 and its note |
| C9 | The preflight cache is keyed by network partition key, origin, URL and credentials | Quote: Fetch, 4.9 |
| C10 | `Vary: Origin` when the requirements are more complicated than `*` or a static origin; without it a cached response lacking the header can be reused for a CORS request; with `*` or a fixed origin for everyone, always send the header and no `Vary` | Quote: Fetch, *CORS protocol and HTTP caches* |
| C11 | CSRF tricks an authenticated user's browser into an unwanted action on a trusted site; form submissions are simple requests browsers send to any origin; synchronizer tokens, double submit cookies and Fetch Metadata headers (`Sec-Fetch-Site`); `SameSite` is defense in depth; `Strict` withholds cookies from cross-site requests | Quote: CSRF cheat sheet, *Introduction*, *Disallowing simple requests*, *Fetch Metadata headers*, *SameSite* |
| C12 | No sensitive content on `Access-Control-Allow-Origin: *`; the header only on URLs that need it; only selected trusted origins, no blind reflection; CORS does not prevent the data going to an unauthorized location; simple requests need access control of their own; do not rely only on `Origin` for access control | Quote: [HTML5 Security Cheat Sheet, Cross Origin Resource Sharing](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html#cross-origin-resource-sharing) |

## Authentication and authorization

Used in `authentication-and-authorization`; A3 and A16 in `secrets-and-redaction` too.

| # | Claim | Source |
|---|-------|--------|
| A1 | Authorization verifies that an action is approved for an entity and is distinct from authentication, which verifies identity; least privilege; deny by default; validate permissions on every request; prefer ABAC and ReBAC over RBAC, ABAC being more effective for least privilege; IDOR; never rely on client-side checks | Quote: [Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html) |
| A2 | `401` lacks valid authentication credentials; `403` understood but refused; a server that wishes to hide a forbidden resource may answer `404` | Quote: [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.txt), 15.5.2 and 15.5.4 |
| A3 | SP 800-63B-4, final, July 2025, supersedes SP 800-63B; something you know, have, are; AAL2 and AAL3 require two distinct factors; single-factor passwords at least 15 characters, with MFA at least 8; no composition rules; no periodic changes, but a change on evidence of compromise; a blocklist of common, expected or compromised passwords | Quote: [CSRC page](https://csrc.nist.gov/pubs/sp/800/63/b/4/final); [SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html), sections 2, 3.1.1 and 3.1.1.2 |
| A4 | A definite overall reauthentication timeout is required at AAL1 and AAL2, recommended at no more than 30 days and 24 hours, with an inactivity timeout recommended at no more than an hour at AAL2; at AAL3 the overall timeout is required to be no more than 12 hours, and inactivity is recommended at no more than 15 minutes | Quote: SP 800-63B-4, sections 2.1.3, 2.2.3 and 2.3.3 |
| A5 | Argon2id with one of several minimum configurations, among them 19 MiB of memory, two iterations and parallelism 1; the configurations give an equal level of defense and trade CPU for RAM | Quote: [Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html), *Argon2id* |
| A6 | The session ID is temporarily equivalent to the strongest authentication method used; at least 64 bits of entropy; meaningless; `Secure`, `HttpOnly`, `SameSite=Strict` or `Lax`; renewed after any privilege level change, against session fixation | Quote: [Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html) |
| A7 | JWT claims `iss`, `sub`, `aud`, `exp`, `nbf`, `iat`, `jti`; reject when `aud` is present and does not identify you; now before `exp`, at or after `nbf`; leeway usually no more than a few minutes; `jti` can prevent replay | Quote: [RFC 7519](https://www.rfc-editor.org/rfc/rfc7519), 4.1.1 to 4.1.7 |
| A8 | An attacker can change the algorithm to `none`; `RS256` changed to `HS256` made some libraries validate with the RSA public key as the HMAC shared secret; libraries must let the caller specify the algorithms and use no other; validate issuer and audience; explicit typing with `typ` (3.11); mutually exclusive validation rules (3.12); cross-JWT confusion (2.8) | Quote: [RFC 8725](https://www.rfc-editor.org/rfc/rfc8725) |
| A9 | OAuth 2.0 lets a third-party application obtain limited access to an HTTP service; refresh tokens are credentials used to obtain access tokens | Quote: [RFC 6749](https://www.rfc-editor.org/rfc/rfc6749), abstract and 1.5 |
| A10 | OpenID Connect is an identity layer on top of OAuth 2.0; the ID token holds claims about the authentication of an end-user; `nonce` associates a client session with an ID token and mitigates replay; `state` maintains state between request and callback, and binding it to a browser cookie mitigates CSRF | Quote: [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html) |
| A11 | RFC 9700, January 2025, a Best Current Practice: public clients must use PKCE; the implicit grant should not be used; the password credentials grant must not be used; exact string matching of redirect URIs; access tokens audience-restricted; public clients' refresh tokens sender-constrained or rotated; rotation issues a new refresh token on every refresh, invalidates the previous one, detects reuse and revokes the active token | Quote: [RFC 9700](https://www.rfc-editor.org/rfc/rfc9700), 2.1, 2.1.1, 2.1.2, 2.2.2, 2.3, 2.4 and 4.14.2 |
| A12 | PKCE mitigates authorization code interception; the code verifier is a high-entropy random string of 43 to 128 unreserved characters; `S256` is `BASE64URL-ENCODE(SHA256(ASCII(code_verifier)))`; a client capable of `S256` must use it, `plain` only when it cannot | Quote: [RFC 7636](https://www.rfc-editor.org/rfc/rfc7636), abstract, 4.1, 4.2, 4.6 |
| A13 | ABAC determines authorization by evaluating attributes of the subject, object, operation and sometimes environment against policy | Quote: [NIST SP 800-162](https://csrc.nist.gov/pubs/sp/800/162/upd2/final), abstract |
| A14 | XACML 3.0 (22 January 2013): PEP, PDP, PAP, PIP; deny-overrides, permit-overrides and first-applicable; decisions Permit, Deny, NotApplicable (no policy applies) and Indeterminate (unable to evaluate, for example missing attributes or network errors while retrieving policies) | Quote: [XACML 3.0](https://docs.oasis-open.org/xacml/3.0/xacml-3.0-core-spec-os-en.html), 1.1.1, 2.3, 5.53; run: `combining_rules.py` |
| A15 | API1:2023: every endpoint that receives an object ID should perform object-level authorization checks; API3:2023's two conditions were previously named Excessive Data Exposure and Mass Assignment, as in the 2019 edition; avoid functions that automatically bind client input; allow changes only to properties the client should update | Quote: [API1](https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization), [API3](https://api-security.owasp.org/editions/2023/en/0xa3-broken-object-property-level-authorization) |
| A16 | Any party in possession of a bearer token can use it; do not pass bearer tokens in page URLs, which browsers and servers may not secure in history and logs | Quote: [RFC 6750](https://www.rfc-editor.org/rfc/rfc6750), abstract, 1.2, 5.3 |

## Secrets, logs and errors

Used in `secrets-and-redaction`; S9 in `threat-modeling`.

| # | Claim | Source |
|---|-------|--------|
| S1 | Secrets include API keys, database credentials, IAM permissions, certificates and SSH keys | Quote: [Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html), 1 |
| S2 | Environment variables are generally accessible to all processes and may be included in logs or system dumps; not recommended unless other methods are not possible; mounted volumes | Quote: same, 5.1 |
| S3 | Rotate regularly so stolen credentials work for a short time; dynamic secrets where possible; restarting does not revoke stolen credentials; user credentials are excluded from regular rotation | Quote: same, 2.4 and 2.7.2 |
| S4 | Secrets get the minimum privileges for their use | Quote: same, 2.7.1 |
| S5 | Exposed keys undergo immediate revocation, then removal; rewriting git history may introduce other problems; secrets in logs need a removal process that keeps log integrity | Quote: same, 9.2 |
| S6 | Secrets detection before commit, at the developer or in a pre-commit hook | Quote: same, 8.1 |
| S7 | Data to exclude from logs: source code, session identification values, access tokens, sensitive personal data, passwords, connection strings, encryption keys, payment data; remove, mask, sanitize, hash or encrypt; hashed session IDs; de-identification by deletion, scrambling or pseudonymization | Quote: [Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html), *Data to exclude* |
| S8 | Sanitize CR, LF and delimiter characters against log injection; encode for the log format; structured formats such as JSON | Quote: same |
| S9 | Always log authentication successes and failures | Quote: same, *Which events to log* |
| S10 | A generic response to the client, details logged on the server | Quote: [Error Handling Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html) |
| S11 | Many regex implementations can be extremely slow, exponentially in the input size, on patterns with a repeated group that repeats or alternates with overlap | Quote: [OWASP, ReDoS](https://community.owasp.org/attacks/Regular_expression_Denial_of_Service_-_ReDoS) |
| S12 | NIST SP 800-122, April 2010; PII: information that can distinguish or trace an individual's identity, and information linked or linkable to an individual | Quote: [CSRC page](https://csrc.nist.gov/pubs/sp/800/122/final); [glossary](https://csrc.nist.gov/glossary/term/personally_identifiable_information) |

## TLS and certificates

Used in `tls-and-certificates`.

| # | Claim | Source |
|---|-------|--------|
| L1 | Authentication (server always, client optionally), confidentiality and integrity; RFC 9846, July 2026, obsoletes RFC 8446 | Quote: [RFC 9846](https://www.rfc-editor.org/rfc/rfc9846), abstract and 1 |
| L2 | The ClientHello carries a list of key exchange shares and the ServerHello the server's share; all handshake messages after the ServerHello are encrypted; the guide's sentence on key exchange (each side sends a public share, both compute the same secret) explains the shared secrets that section 2 says the handshake establishes | Quote: RFC 9846, 1.3 and 2 |
| L3 | CertificateVerify is a signature over the entire handshake with the private key of the certificate, explicit proof of possession; Finished provides key confirmation and binds the endpoint's identity to the exchanged keys | Quote: RFC 9846, 2, 4.5.2 and 4.5.3 |
| L4 | Detailed certificate validation is out of scope for TLS, see RFC 5280 | Quote: RFC 9846, 4.5.1.3 |
| L5 | All public-key key exchanges provide forward secrecy; static RSA and Diffie-Hellman cipher suites are removed; forward secrecy keeps the session key secure if long-term keying material is compromised after the handshake; for 0-RTT data the protocol gives no forward secrecy guarantee and no guarantee of non-replay between connections | Quote: RFC 9846, 1.3, 2.3 and Appendix F.1 |
| L6 | A certificate the endpoint would need to validate with an MD5-based signature algorithm aborts the handshake with `bad_certificate`; SHA-1 is deprecated and the same abort is recommended; endpoints can accept these algorithms for self-signed certificates and trust anchors | Quote: RFC 9846, 4.5.1.3 |
| L7 | Certificates bind public keys to subjects; validity from `notBefore` through `notAfter`, inclusive; `cA` says whether the key may verify certificate signatures; `pathLenConstraint` is the maximum number of non-self-issued intermediates that may follow; `keyCertSign`; if `cA` is not asserted `keyCertSign` must not be; a CRL is a time-stamped, signed list of revoked certificates | Quote: [RFC 5280](https://www.rfc-editor.org/rfc/rfc5280), 3.1, 3.3, 4.1.2.5, 4.2.1.3, 4.2.1.9 |
| L8 | The trust anchor is an input, its name and public key; per certificate: signature, validity, not revoked, issuer name; per intermediate: basic constraints with `cA` true, `max_path_length` above zero and decremented for non-self-issued certificates, lowered by `pathLenConstraint`, `keyCertSign` when key usage is present | Quote: RFC 5280, 6.1, 6.1.3 (a)(1) to (4), 6.1.4 (k) to (n) |
| L9 | RFC 9525, November 2023, obsoletes RFC 6125; the Common Name must not identify a service; the wildcard is the complete left-most label, matches one label, and an identifier that breaks the rules must be ignored; case-insensitive ASCII comparison; wildcard certificates vouch for single-label names, not deeper levels, risking rogue hosts | Quote: [RFC 9525](https://www.rfc-editor.org/rfc/rfc9525), 2, 6.3, 7.1 |
| L10 | RFC 4158 (Informational, September 2005): path building, unlike validation, is not addressed by the standards | Quote: [RFC 4158](https://www.rfc-editor.org/rfc/rfc4158) |
| L11 | OCSP gives a certificate's status without CRLs; `good`, `revoked`, `unknown`, the last usually for an issuer the responder does not serve | Quote: [RFC 6960](https://www.rfc-editor.org/rfc/rfc6960), abstract and 2.2 |
| L12 | Certificate Transparency 2.0 logs TLS server certificates publicly so that anyone can audit CAs and notice suspect certificates; obsoletes RFC 6962 | Quote: [RFC 9162](https://www.rfc-editor.org/rfc/rfc9162), abstract |
| L13 | NIST SP 800-52 Rev. 2, August 2019: TLS 1.2 support required of government servers and clients, TLS 1.3 support by January 1, 2024; its page notes, on 2026-05-07, that it is being reviewed | Quote: [CSRC page](https://csrc.nist.gov/pubs/sp/800/52/r2/final) |
| L14 | A digital signature: the private key signs, the public key verifies; authenticity, integrity and non-repudiation, not confidentiality or replay protection | Quote: [NIST glossary, digital signature](https://csrc.nist.gov/glossary/term/digital_signature), the SP 800-63-4 entry |

## Threat modeling and principles

Used in `threat-modeling`; N1 and N2 in `trust-boundaries-and-injection`, N1 in `authentication-and-authorization` too.

| # | Claim | Source |
|---|-------|--------|
| M1 | Threat modeling is analyzing representations of a system to highlight concerns about security and privacy characteristics; the four questions; the values: finding and fixing design issues over checkbox compliance, people and collaboration over processes, methodologies and tools, a journey of understanding over a snapshot, doing over talking, continuous refinement over a single delivery | Quote: [Threat Modeling Manifesto](https://www.threatmodelingmanifesto.org/) |
| M2 | The four questions, from the Manifesto; DFDs with trust boundaries, data flows, data stores, processes and external entities; STRIDE paired with authentication, integrity, accounting, confidentiality, availability and authorization; mitigate, eliminate, transfer, accept; ranking in theory by likelihood times impact, hard to estimate; ideally in the design phase, maintained alongside the system | Quote: [Threat Modeling Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html) |
| M3 | ASVS 5.0.0, published 30 May 2025; seventeen chapters, V1 Encoding and Sanitization to V17 WebRTC; Level 1 around 20% of the requirements, first-layer defenses; most applications should strive for Level 2, around 70% with Level 1; Level 3 the final ~30%, for the highest levels of security; the organization chooses its level; forks encouraged with traceability | Quote: [asvs.owasp.org](https://asvs.owasp.org/); [`0x03-What-is-the-ASVS.md` at `v5.0.0_release`](https://github.com/OWASP/ASVS/blob/v5.0.0_release/5.0/en/0x03-What-is-the-ASVS.md) and the chapter files at that tag |
| M4 | Consistent message and timing for existing and missing accounts; per-account rate limits; tokens random from a safe algorithm, long, stored securely, single use, expiring; `Referrer-Policy: no-referrer`; no change to the account before a valid token; the URL hard-coded or validated against trusted domains | Quote: [Forgot Password Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html) |
| N1 | Least privilege, fail-safe defaults ("base access decisions on permission rather than exclusion"), complete mediation ("every access to every object must be checked for authority"), economy of mechanism, separation of privilege, open design | Quote: [Saltzer and Schroeder, *Basic Principles*](https://web.mit.edu/Saltzer/www/publications/protection/Basic.html); the year from the [course copy](https://www.cs.virginia.edu/~evans/cs551/saltzer/), "revised April 17, 1975" and "Copyright © 1975" |
| N2 | Attack surface: where an attacker can try to enter, cause an effect on, or extract data from a system | Quote: [NIST glossary](https://csrc.nist.gov/glossary/term/attack_surface), SP 800-53 Rev. 5 |
| N3 | Defense in depth: multiple countermeasures in a layered or stepwise manner, so attacks missed by one are caught by another | Quote: [NIST glossary](https://csrc.nist.gov/glossary/term/defense_in_depth), the NISTIR 8183 entry |
| N4 | Risk is typically a function of adverse impact and likelihood | Quote: [NIST glossary](https://csrc.nist.gov/glossary/term/risk), SP 800-30 Rev. 1 |
| N5 | FIPS 199 (February 2004) categorizes by confidentiality, integrity and availability | Quote: [CSRC page](https://csrc.nist.gov/pubs/fips/199/final), abstract |

## Python

The documentation at docs.python.org/3, for 3.13 and later. Each module is cited in the guide that uses it.

| # | Claim | Source |
|---|-------|--------|
| P1 | `sqlite3`: string operations to build queries are vulnerable to SQL injection; qmark and named placeholders; `execute` runs a single statement and raises `ProgrammingError` for more; `executescript` for several; `":memory:"` | Quote: [sqlite3](https://docs.python.org/3/library/sqlite3.html); run: `query_injection.py` |
| P2 | `subprocess` never implicitly calls a shell; with `shell=True` quoting is the application's responsibility; a sequence of arguments is generally preferred; on one operating system, batch files may run in a shell regardless | Quote: [subprocess](https://docs.python.org/3/library/subprocess.html), *Security Considerations*, *Frequently Used Arguments*; run: `argument_lists.py` |
| P3 | `shlex.quote` is only for Unix shells and can open command injection elsewhere, use argument lists; `punctuation_chars` (3.6) returns runs of `();<>|&` as tokens; `whitespace_split` | Quote: [shlex](https://docs.python.org/3/library/shlex.html); run: `argument_lists.py` |
| P4 | `html.escape` converts `&`, `<`, `>`, and with `quote=True` also `"` and `'`; `html.unescape` follows HTML5 rules | Quote: [html](https://docs.python.org/3/library/html.html); run: `what_the_parser_sees.py` |
| P5 | `urlencode` quotes with `quote_plus` by default: spaces as `+`, `/` as `%2F`; `parse_qs` parses form-encoded queries | Quote: [urllib.parse](https://docs.python.org/3/library/urllib.parse.html); run: `what_the_parser_sees.py` |
| P6 | `ensure_ascii`, the default, escapes every non-ASCII and non-printable character; the documented escapes do not include `/` or `<` | Quote: [json](https://docs.python.org/3/library/json.html); run: `json_data_block.py` |
| P7 | `hmac.compare_digest` avoids content-based short-circuiting against timing analysis | Quote: [hmac](https://docs.python.org/3/library/hmac.html) |
| P8 | Prefer `secrets` to `random`, designed for modelling and simulation; 32 bytes believed sufficient as of 2015; `DEFAULT_ENTROPY` subject to change | Quote: [secrets](https://docs.python.org/3/library/secrets.html); run: `hashed_secrets.py` |
| P9 | A filter may modify the record in place or, since 3.12, return a new record; logger filters are not consulted for events of descendant loggers; handler filters are consulted before the handler emits | Quote: [logging](https://docs.python.org/3/library/logging.html), *Filter Objects*; run: `log_redaction.py` |
| P10 | `create_default_context()` is recommended for clients, enabling certificate validation and hostname checking; 3.10 made TLS 1.2 the minimum for `PROTOCOL_TLS`, `_CLIENT` and `_SERVER`; `verify_mode` cannot go back to `CERT_NONE` while `check_hostname` is on; `CERT_REQUIRED` alone is not sufficient; servers must require client certificates to authenticate clients; `hostname_checks_common_name` defaults to true; since 3.7 hostname matching happens in the handshake and `match_hostname()` is no longer used | Quote: [ssl](https://docs.python.org/3/library/ssl.html), *Best defaults*, *Verifying certificates*, `SSLContext`, `do_handshake`; run: `client_settings.py` |

## The examples and the arithmetic

| # | Claim | Source |
|---|-------|--------|
| E1 | `x' OR 1=1 --` returns all four orders glued and none bound; `d'arcy` gives `near "arcy": syntax error` glued; the sort allowlist refuses `total; DROP TABLE orders` | Run: `query_injection.py` |
| E2 | The child process received one argument; the shell tokens split at `;` | Run: `argument_lists.py` |
| E3 | The parser's tokens for raw and encoded text, unquoted and quoted attributes, and the two queries | Run: `what_the_parser_sees.py` |
| E4 | `json.dumps` leaves `</script`; the escaped form round-trips | Run: `json_data_block.py` |
| E5 | The sharing table of the four servers | Run: `cors_check.py` |
| E6 | Accepted, refused for a bad signature, refused for the wrong audience | Run: `signed_token.py` |
| E7 | First-applicable flips with the order; deny- and permit-overrides do not; no rule applies to the public document | Run: `combining_rules.py` |
| E8 | The logger filter misses the child logger's line; the handler filter masks both | Run: `log_redaction.py` |
| E9 | A 32-byte token is 43 characters, its SHA-256 64 hex digits; the code 4071 is found after 4,072 hashes | Run: `hashed_secrets.py` |
| E10 | The four primes pass trial division; the genuine certificate checks; the edited and the forged ones fail | Run: `toy_signatures.py` |
| E11 | The default context's settings, the `ValueError`, and `CERT_NONE` for a server context | Run: `client_settings.py`, with the interpreter's own TLS library |
| E12 | Four boundary crossings; the ranked threats | Run: `reset_threat_model.py` |
| E13 | Longest outputs: 6 characters for `&quot;`, 12 for four `%HH`, 6 for one `\u` escape and 12 for a pair | Arithmetic |
| E14 | 10^4 four-digit codes, 10^10 ten-digit numbers, 2^256 values of 32 random bytes | Arithmetic |
| E15 | Six STRIDE questions for each of b crossing flows: 24 for four | Arithmetic |

## Citations and names

The guides name no company, product or vendor. Where they name an organization or a document, it is the publisher of an open standard, an RFC, a public guideline or the language of the examples:

| Name | Why it is named |
|------|-----------------|
| OWASP | Publisher of the cheat sheets, the Top 10, the API Security Top 10 and ASVS, the sources of most claims; the AI engineering path names it too |
| NIST, FIPS | Publishers of SP 800-63B-4, 800-162, 800-122, 800-52 Rev. 2, FIPS 199 and the glossary entries |
| WHATWG standards | The HTML, Fetch and URL Standards, named as "the HTML Standard", "the Fetch Standard" and "the URL Standard" |
| XACML 3.0 | An open standard, named for its architecture and combining algorithms; the guide does not name its publishing consortium |
| OpenID Connect, OAuth 2.0, JWT, PKCE | Open protocols, cited by their specifications |
| Saltzer and Schroeder | Authors of the 1975 paper, cited by name as papers are in the other guides |
| Python | The language of the examples, with its official documentation |

Choices at the edges:

- STRIDE is named as a mnemonic, without its origin. The OWASP cheat sheet attributes the four responses to a named author; the guide does not name him.
- The XSS cheat sheet recommends a specific HTML sanitizer by name; the guide says "a maintained HTML sanitizer".
- Python's documentation names the TLS library that matches hostnames since 3.7; the guide says "the underlying TLS library".
- Python's `subprocess` documentation names one operating system in its note on batch files; the guide says "on some operating systems".
- The examples use reserved `.example` domains, and sample secrets without the prefixes of any real service.
- The ASVS levels are cited from the OWASP repository's file at the `v5.0.0_release` tag; the project's site gives the version and its date.

## Not stated, for lack of a source

- Sections 1 and 2 of RFC 9846 give no round-trip count for the full handshake, so the TLS guide gives none.
- The OWASP Threat Modeling Cheat Sheet pairs repudiation with "accounting", not "non-repudiation"; the threat modeling guide uses its word.
- Python's documentation of `create_default_context` does not itself say that it enables `check_hostname`; the TLS guide relies on the *Best defaults* section and on the run.
- The OWASP Logging Cheat Sheet does not list password changes among the events to log, and the Forgot Password Cheat Sheet does not discuss logging; the threat modeling guide cites authentication successes and failures.
- The CSRF cheat sheet does not say that the same-origin policy or CORS prevents CSRF; the CORS guide says that the policy does not stop it.
- RFC 6454 does not say "send but not read the response"; the CORS guide quotes section 3.4.2 instead.
- The rules of `SameSite` beyond the CSRF cheat sheet's description belong to RFC 6265bis, which is not among the sources; the CORS guide says only that the attribute is about cross-site requests.
- XACML's deny-unless-permit and permit-unless-deny are not among the parts read, and the guide does not mention them.
- RFC 9525 does not say in words that `*.shop.example` does not match `shop.example`; the TLS guide states it as following from "can only match one label".
- The part of the HTML image algorithm read covers one step that fires `error`, so the encoding guide does not say exactly when a broken image fires it.
- RFC 3986 does not say that a fragment is not sent to the server; the encoding guide says that the RFC leaves it to the user agent alone.
- The position of "deny by default" in A01's list of preventions is not among the facts checked; the guide says "among its preventions".
- The copies of Saltzer and Schroeder's paper print no venue; the guides cite its title, authors and year.
- NIST's glossary has no entry for "trust boundary"; the first guide defines it in its own words.
- The OWASP API Security Top 10 does not use the term IDOR; the guide takes the term from the Authorization Cheat Sheet.
- No HTML Standard text among the sources says that a `data:` URL has an opaque origin; the CORS guide rests that on RFC 6454's unique identifier for a URI without a naming authority.
- The SQL cheat sheet does not use the term "second-order injection", so the guide describes stored data without naming it.

## Practice links

The guides and the path practise sixteen problems of the catalog. Each names its guides in the `guides:` list of its `meta.yaml`, after `related:`, and each practice line was checked against the problem's statement:

| Problem | `guides:` |
|---------|-----------|
| `memory-write-sanitizer` | `[llm-application-security, trust-boundaries-and-injection]` |
| `sql-guard` | `[llm-application-security, trust-boundaries-and-injection]` |
| `fix-the-flaws-typescript` | `[trust-boundaries-and-injection, secrets-and-redaction, threat-modeling]` |
| `output-encoding-by-context` | `[output-encoding]` |
| `cors-policy-evaluator` | `[same-origin-and-cors]` |
| `token-claim-validator` | `[authentication-and-authorization]` |
| `refresh-token-rotation` | `[authentication-and-authorization]` |
| `oauth-pkce-client-typescript` | `[authentication-and-authorization]` |
| `payment-webhook-receiver-typescript` | `[authentication-and-authorization]` |
| `authorization-policy-engine` | `[authentication-and-authorization]` |
| `tool-permission-gate` | `[tools-and-mcp, harness-engineering, authentication-and-authorization]` |
| `multi-tenant-api-typescript` | `[authentication-and-authorization, threat-modeling]` |
| `safe-redaction-python` | `[prompts-and-structured-outputs, evaluating-llm-applications, llm-application-security, secrets-and-redaction]` |
| `cert-chain-validator` | `[tls-and-certificates]` |
| `ssrf-safe-webhook-dispatcher-typescript` | `[threat-modeling]` |
| `secure-file-upload-typescript` | `[threat-modeling]` |

## Where a guide comes close to a linked problem

Each guide teaches its idea with examples of its own, after reading the linked problems' statements, hints and solutions. Some ideas are the problems' subject, and some standards the guides cite are the ones the statements quote. These are the places the review should weigh against the rule that a guide never gives away a linked problem's solution:

| Problem | Guide | What the guide shows | Kept back |
|---------|-------|----------------------|-----------|
| `memory-write-sanitizer` | `trust-boundaries-and-injection` | That delimiters around stored text are structure to a model, as quotes are to SQL | Removing delimiters until none is left, the joined-text case, the length cap and the role-marker flags |
| `sql-guard` | `trust-boundaries-and-injection` | Bound values with `sqlite3`, and an allowlist that maps a sort choice to fixed SQL | The tokenizer, the single-`SELECT` rule, the table and column allowlist over parsed SQL, row limits and the placeholder flags |
| `fix-the-flaws-typescript` | `trust-boundaries-and-injection`, `secrets-and-redaction`, `threat-modeling` | Level 3's idea, bound values, in Python with other strings (`x' OR 1=1 --`, and a name with an apostrophe as in the statement's `O'Brien`); decoding before checking a path, without code (near hint 3); a redaction filter on the handler and the `Authorization` header in logs (near hint 6); generic errors with details in the log, as level 4 expects | The service's code, every fix, path resolution and containment, which fields an account takes |
| `output-encoding-by-context` | `output-encoding` | The five HTML replacements and the unreserved characters, as the statement lists them; `html.escape` in the example, which produces the HTML rule in Python (the solution's language notes say so) | The URL rule in code (the example uses `urlencode`, which writes `+`, unlike the problem's `%20`), the defaults of `quote`, which hint 3 asks the solver to check, the JavaScript rule (UTF-16 code units, the allowlist of letters and digits, uppercase hex) and the refusal of unknown contexts |
| `cors-policy-evaluator` | `same-origin-and-cors` | The browser's CORS check from Fetch, against four server answers, one of them an exact set of origins (the statement's level 1 rule and close to hint 2); the safelist and the credentials rules in prose, as the statement gives them | Origin serialization and its grammar, `needsPreflight` and `preflightResponse` as code, row order, the four-rule decision with `Vary`, method and header wildcards in code, patterns and the linter |
| `token-claim-validator` | `authentication-and-authorization` | RFC 7519's `exp` (before) and `nbf` (at or after) with a few minutes' leeway, which is close to hint 3; an audience check in the toy token | The problem's rule order, malformed and missing claims, the digit check of hint 2, the skew formulas and scopes |
| `refresh-token-rotation` | `authentication-and-authorization` | RFC 9700's rotation and reuse detection, as the statement describes them | The grace window, its tie-breaks, families and the lifecycle of ids |
| `oauth-pkce-client-typescript` | `authentication-and-authorization` | PKCE's verifier length and `S256` from RFC 7636, `state` and `nonce` from OpenID Connect, as level 1 states them | The endpoints, cookies and sessions, the ID token checks and their order, key rotation, refresh, revocation and logout |
| `payment-webhook-receiver-typescript` | `authentication-and-authorization` | That a receiver recomputes the signature with the shared secret and checks a timestamp against replay | The header format, the tolerance, the check order, duplicates, ordering and reconciliation |
| `authorization-policy-engine` | `authentication-and-authorization` | Deny-overrides over two flat attribute rules, with "no rule applies" kept apart, which the statement's three steps define | Role inheritance and its cycles (hint 2), resource ancestors and wildcards, and the walk that finds applicable rules |
| `tool-permission-gate` | `authentication-and-authorization` | Its practice line only | Every rule of the gate |
| `multi-tenant-api-typescript` | `authentication-and-authorization`, `threat-modeling` | `404` for another tenant's object and row-level policies as a second check, both in the statement; mass assignment in OWASP's words | The policies, the per-transaction setting, pooled connections, the migration and the roles |
| `safe-redaction-python` | `secrets-and-redaction` | That detectors miss, that patterns suit fixed-shape data such as emails and models suit names, and that what a redactor misses matters most, all ideas the statement gives | Span replacement, quote checks, merging, the patterns and the F2 score |
| `cert-chain-validator` | `tls-and-certificates` | RFC 5280's path checks and RFC 9525's name rules, which the statement also gives; signatures with toy RSA, which the problem gives as data | Chain search, the order of chains, the problem's reasons and their order, path-length bookkeeping in code, revocation and `verify`'s report |
| `ssrf-safe-webhook-dispatcher-typescript` | `threat-modeling` | Its practice line, and that the Top 10:2025 maps SSRF into A01 | Address ranges, name resolution, redirects and limits |
| `secure-file-upload-typescript` | `threat-modeling` | Its practice line only | Size limits, names, magic numbers, quarantine and links |
| `output-encoding-by-context`, follow-up 1 | `output-encoding` | That a URL from a user needs its scheme checked against an allowlist (`http` and `https`) before it goes into an attribute, and that each parameter value is encoded, not the whole URL | How the problem's `url-query` rule would break a whole URL |
| `cors-policy-evaluator`, follow-up 1 | `same-origin-and-cors` | That a browser sends a serialized origin, so a server compares it whole and never normalizes or parses it | What the server parses instead |
| `fix-the-flaws-typescript`, follow-up 2 | `secrets-and-redaction` | Keeping only the SHA-256 of each random token, so that a copy of the database gives no usable token | The service's schema and its migration |
| `refresh-token-rotation`, follow-up 4 | `secrets-and-redaction` | The same: a store that keeps only a hash of each token | What changes in the store's lookups and its grace retries |
| `fix-the-flaws-typescript`, hints 3 to 6 | `trust-boundaries-and-injection`, `authentication-and-authorization`, `secrets-and-redaction` | Hint 3: decode a name before checking it (the first guide's trap); hint 4: allow changes only to the properties a client should update (the authorization guide's trap, in the words of OWASP's API3); hint 5: bound values (the first guide's example); hint 6: the `Authorization` header carries a token into the log (the secrets guide's example) | The code of every fix, path resolution and containment, and the account's fields |

## Independent accuracy review (2026-11-13)

The review checks every claim of the seven guides against the source this page gives for it, runs the twelve examples and compares what they print with the guides, and reads the guides against the linked problems' statements, hints, follow-ups and solutions. All twelve examples match, no example models an insecure practice without saying so, and the metadata is consistent. These are its fourteen findings and where each is applied.

| # | Finding | Where it is applied |
|---|---------|---------------------|
| 1 | TLS 1.3 is defined by RFC 9846 (July 2026), which obsoletes RFC 8446 | `tls-and-certificates` cites RFC 9846 and says that it obsoletes RFC 8446; L1 to L6 give its sections |
| 2 | ADR 0025's count of paths includes this one | It says "Eleven more paths" |
| 3 | Only some of NIST's reauthentication limits are requirements | The overall timeout is required at every level; the limits at the two lower levels and the inactivity limits are recommended, and the 12-hour limit at the highest level is required (A4) |
| 4 | The cheat sheet lists several equivalent minimum settings for Argon2id | 19 MiB, two iterations and one degree of parallelism are given as one of them, in the text and in the complexity table (A5) |
| 5 | An error ID in the client's answer has no source and conflicts with `fix-the-flaws-typescript` level 4 | The secrets guide's trap says to return a generic error and keep the message and the stack trace in the log |
| 6 | The 2019 edition of the API Security Top 10 names the problem in part as mass assignment | The authorization guide says so (A15) |
| 7 | The guides name no product, operating systems included | The first guide says "on some operating systems", and the citations section records the choice |
| 8 | This page describes what the guides do not state in the present tense | Its section is "Not stated, for lack of a source" |
| 9 | Where a guide answers a linked problem's follow-up or hints, this page says so | The encoding guide's trap on whole URLs says only to encode each parameter value, not the entire URL; the table of places close to a problem lists the follow-ups and hints the guides answer |
| 10 | Jargon is defined at first use | The first guide introduces OWASP and NIST, the encoding guide an RFC |
| 11 | A key share needs a definition before the handshake | The TLS guide defines key exchange and key shares before the handshake |
| 12 | The encoding guide's first table needs the tokenizer's states | A sentence on the tokenizer's states leads into it |
| 13 | The exemptions from the weak-signature rules have a reason | Neither rule applies to self-signed certificates or trust anchors, whose signatures the client does not need to validate (L6) |
| 14 | The toy token leaves out the time claims | The authorization guide says that a real check must apply `exp` and `nbf` |
