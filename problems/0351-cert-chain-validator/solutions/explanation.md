# Certificate Chain Validator: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| search-then-validate | optimal | O(K n C) per verify | O(C + K n) | default answer |

`C` is the number of certificates (with their signatures), `K` the number of chains from the leaf, and `n` the length of the longest one.

## How the design grows level by level

| Level | Change | What the validator adds |
|-------|--------|-------------------------|
| 1 | One certificate | A date check with both ends included, and a name matcher with the wildcard rules |
| 2 | Chains | A graph whose edges are a name match plus a recorded valid signature, and a search for every chain to the first anchor, sorted |
| 3 | Constraints | A walk from the anchor down to the leaf in the order of RFC 5280, with the remaining path length as state |
| 4 | Revocation and choice | One more check in the walk, and a loop over the sorted chains that records why each failed |

The early choice that matters is to separate **building** from **validating**. Building finds candidate chains from names and signatures only; validating decides whether one chain is acceptable. RFC 5280 is written the same way: it defines validation of a given path and leaves path building out of scope. With the two apart, level 4 is a loop that feeds the first into the second.

## Approach: search-then-validate (Enumerate the chains shortest first then validate each in the order of RFC 5280)

### Intuition

A certificate is a claim, "this key belongs to this name", and a signature is someone vouching for the claim. Trust flows down from the anchors: an anchor vouches for an intermediate, which vouches for the next, down to the leaf. Each check in path validation asks one question about one step of that flow: did the voucher really sign (signature), was the claim current (dates), was it withdrawn (revocation), is the voucher the one the claim names (issuer name), was the voucher allowed to vouch for others (CA flag, key usage), and had the chain already grown longer than an earlier voucher allowed (path length). The hostname is the final question, about the claim at the bottom.

Walking from the anchor down mirrors that flow, and it is what makes the path length simple: each CA's `pathLen` only limits what comes *after* it, so a single counter that is decremented and capped on the way down answers the question for every certificate.

### Algorithm

1. Names: lowercase and split on dots. Without `*`, the label lists must be equal. With `*`, the name is usable only when its first label is exactly `*`, no other label has a `*`, and at least two labels follow; then the hostname must have one more label and the same labels after its first.
2. Links: the issuers of `C` are the certificates whose subject equals `C`'s issuer and whose signature on `C` is recorded as valid.
3. Chains: depth-first from the leaf; append an issuer not already on the chain; record the chain when its last certificate is an anchor, and do not go past it. Sort by length, then by the list of ids.
4. `validatePath`: check the structure (unknown ids, a repeated id, the last one an anchor). Reverse the path. For each certificate after the anchor, with the previous one as signer: signature, dates, revocation, issuer name; and for an intermediate: CA flag, remaining length (decrement when not self-issued, fail at 0), cap by `pathLen`, `keyCertSign`. Then the hostname.
5. `verify`: for each sorted chain, validate and append `[reason, certId, ...chain]`; stop at the first `ok`.

### Correctness

Chains: the search follows exactly the links of the statement, never revisits a certificate on the current chain, and stops at the first anchor, so it produces exactly the statement's chains, each once. Sorting by `(length, ids)` is a total order on distinct chains, so the first one and the order of `verify` are unique.

Validation: each check is the statement's, tested in the statement's order, and the function returns at the first failure, so the reason and the certificate are those of the first failing check. The remaining length starts at `n` and is decremented once per non-self-issued intermediate before that certificate's own `pathLen` caps it, which is RFC 5280's steps (l) and (m) in that order: a `pathLen` of `p` on a certificate therefore allows exactly `p` more non-self-issued intermediates below it, and the leaf, which is never checked against it, does not count. The anchor is never processed, so its dates, constraints and revocation cannot fail a chain.

`verify`: it validates the chains in `buildChain`'s order and stops at the first success, so it returns the shortest valid chain, ties broken by ids, preceded by every shorter or earlier chain with its reason.

### Complexity

- Time: O(K n C) per verify — the search does at most `n` steps per chain and scans the `C` certificates for issuers at each; sorting costs O(K log K) comparisons of chains; validating a chain is O(n) plus the hostname check.
- Space: O(C + K n) — the certificates and signatures, and the `K` chains of at most `n` ids.

### Trade-offs

- Enumerating every chain before validating any is simple and gives `verify` its full report, but the number of chains can grow quickly in a pool with much cross-signing. A production builder searches lazily, prunes on checks that do not depend on the rest of the chain (dates, revocation, the CA flag), and bounds the work it will do.
- Shortest first, then by id, is a deterministic policy, not the only good one. Real builders often prefer chains to anchors they rank higher, or certificates with later expiry, and try candidates in an order that is likely to succeed first.
- Recording signatures as data keeps the problem about logic. In a real validator the signature check is the expensive step, so it is usually done once per pair and cached, which is what the map of recorded results stands for.
- Reporting every refused chain helps an operator see that, say, an old cross-sign expired. A client should not show all of it to the user, but logging it is how such outages are diagnosed.

### Pitfalls and edge cases

- **Inclusive dates.** `notAfter` itself is valid, one second later is not, and a certificate whose period is a single second is valid at that second (`ex1`, `h1`). The order is dates before the hostname (`h1`).
- **Wildcards.** One label, only on the left, only as the whole label, only once (`ex2`, `h2`, `h6`). `*.shop.example` does not cover `shop.example` (`h6`), and `*.example` is ignored by this problem's two-label rule (`h2`). Case is ignored on both sides, and the matched entry is returned as written (`h4`).
- **The common name.** A subject `CN=shop.example` with no matching DNS name is a mismatch (`h3`).
- **A taken id.** `addCertificate` refuses it and keeps the first certificate (`h5`).
- **Links need both.** A name without a recorded valid signature is no link (`ex4`, `h8`, `h9`), and a valid signature under a different name is no link either (`h10`, where the names differ only in case). A signature recorded the other way round does not count (`h9`).
- **Loops and cross-signing.** Two CAs that signed each other must not send the search in circles (`h11`); two anchors with the same subject give two chains of equal length, ordered by id (`h7`).
- **Shortest first.** A shorter chain wins over one with smaller ids (`h8`), and a chain stops at the first anchor even if a longer one would continue (`h12`).
- **Structure before content.** Unknown ids come before repeated ones, which come before an untrusted end (`h14`).
- **Order within a certificate.** Signature, then dates, then revocation, then issuer name (`h15`, `h25`); a certificate closer to the anchor is reported before one closer to the leaf (`h16`).
- **Only intermediates are constrained.** The leaf may be a CA or not and have any key usage, and the anchor's constraints and dates are ignored (`h18`, `h19`).
- **Path length.** It counts non-self-issued intermediates *below* the certificate, the leaf excluded; a self-issued intermediate does not count (`ex6`, `h17`, `h24`). Comparing at the wrong place, or counting the leaf, is off by one.
- **Key usage.** An absent extension allows everything; a present one must include `keyCertSign` (`h18`, `h24`). The CA flag is checked first (`h18`).
- **Revocation.** It is part of path validation, after the dates, and never applies to the anchor (`h21`, `h22`, `h25`, `h26`); `checkLeaf` ignores it (`h21`).
- **`verify` stops at the first success** and reports every earlier failure, including a hostname mismatch on each chain when no name matches (`h23`, `h24`).

### Language notes

- Python: a list of labels compares with `==`, and lists of ids compare lexicographically, so `sorted(chains, key=lambda c: (len(c), c))` is the whole ordering. A dictionary keyed by the tuple `(signer, cert)` holds the signatures.
- TypeScript: arrays compare by reference, so label lists are compared after `join(".")` and chains with an explicit comparator. Tuples are not hashable keys in a `Map`, so the pair is encoded as one string (`JSON.stringify([signer, cert])` cannot collide). `Array.prototype.sort` with a comparator is stable and deterministic.

## Further reading

- [RFC 5280, Internet X.509 Public Key Infrastructure Certificate and Certificate Revocation List (CRL) Profile](https://www.rfc-editor.org/rfc/rfc5280): section 3.1 (what a certificate binds), 4.1.2.5 (validity, both ends inclusive), 4.2.1.3 (key usage and `keyCertSign`), 4.2.1.9 (basic constraints and `pathLenConstraint`), 6.1 (path validation, self-issued certificates, the trust anchor as an input), 6.1.3 and 6.1.4 (the order of the checks), and 7.1 (how real implementations compare names).
- [RFC 9525, Service Identity in TLS](https://www.rfc-editor.org/rfc/rfc9525): section 2 (the common name must not be used to identify a service), 6.3 (matching DNS names and the wildcard rules) and 7.1 (the security of wildcard certificates). It obsoletes RFC 6125.
- [RFC 4158, Internet X.509 Public Key Infrastructure: Certification Path Building](https://www.rfc-editor.org/rfc/rfc4158): the part RFC 5280 leaves out, with cross-certified and bridge structures and strategies for ordering candidate paths.
- [RFC 6125](https://www.rfc-editor.org/rfc/rfc6125), the earlier version of the service identity rules, which still allowed a wildcard as part of a label and the common name as a fallback.
