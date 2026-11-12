# Certificate Chain Validator

## Statement

Build `ChainValidator`, the part of a TLS client that decides whether to trust the certificate a server presents. There is no cryptography here: whether a signature checks out is given to you as data, and your job is everything around it, which is where most certificate bugs live. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**What a certificate proves.** When you connect to `https://shop.example`, the server sends a **certificate**: a small signed document that says "this public key belongs to `shop.example`". Your client can then check that the server holds the matching private key, but that only helps if the certificate itself can be believed. It is believed because someone the client already trusts signed it: a **certificate authority** (CA). A certificate names its **subject** (who it is about) and its **issuer** (the CA that signed it), the **validity period** in which it may be used, and in a *subject alternative name* extension the DNS names it is for.

The CA that signed the server's certificate is usually not one the client knows directly. Its own certificate was signed by another CA, and so on, until one of them is a **trust anchor**: a CA certificate that the client was configured to trust, for example from the operating system's root store. So the client must find a **chain** from the server's certificate (the **leaf**) up to a trust anchor, check that every link is a real signature by a certificate that is allowed to sign certificates, and check that every certificate in it is in date and not withdrawn.

A mistake in any of these checks lets an attacker who can intercept the connection present a certificate that the client accepts for a site it was never issued for.

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 35, level 2 by 65, level 3 by 95 and level 4 by 115, keeping the last minutes for a final run.

## Input

- `ChainValidator()`: creates a validator with no certificates.
- A certificate is identified by an id of your choosing (`certId`, `signerId`, `leafId`), 1 to 20 characters from `a` to `z`, `0` to `9` and `-`. Ids compare by character codes.
- Subjects and issuers are distinguished names written as text, such as `CN=Example Root`. Two names are the same only when the texts are exactly equal. (Real implementations compare names attribute by attribute with rules for case and spaces; here the names are opaque text.)
- Times (`notBefore`, `notAfter`, `now`) are whole numbers on one clock, in seconds; any unit works. The validator never reads a clock.
- Hostnames are 1 to 253 characters: labels of ASCII letters, digits and `-`, separated by single dots, with no dot at either end.
- Each level's section describes the methods it adds and their parameters.

## Output

- Reasons are lowercase words such as `expired`, and `ok` when every check passes.
- A method that returns text returns `""` for "nothing", and one that returns a list returns `[]`.

## Level 1: One certificate

- `addCertificate(certId, subject, issuer, notBefore, notAfter, dnsNames)`: stores a certificate. `dnsNames` are the DNS names of its subject alternative name extension, in order. Returns `true`, or `false` when `certId` is already taken, in which case nothing changes.
- `matchedName(certId, hostname)`: the first entry of `dnsNames`, in order and exactly as written, that matches `hostname`. `""` when none matches or the certificate is unknown.
- `checkLeaf(certId, hostname, now)`: checks one certificate on its own, and returns the first failing reason in this order: `unknown-certificate`, `not-yet-valid` (`now < notBefore`), `expired` (`now > notAfter`), `hostname-mismatch` (`matchedName` is `""`), else `ok`.

**Dates.** The validity period runs from `notBefore` through `notAfter`, **both included** (RFC 5280): a certificate is still valid at the exact second of `notAfter`.

**Names** (RFC 9525, section 6.3). A DNS name matches a hostname when they have the same labels, compared without regard to ASCII case: `Shop.EXAMPLE` matches `shop.example`. A name may contain the **wildcard** `*`, which matches **exactly one** label of the hostname, under these rules:

- There is exactly one `*`, and it is the whole left-most label: `*.shop.example`. A name with `*` anywhere else, with two of them, or as part of a label (`f*.shop.example`, `www.*.shop.example`, `*.*.shop.example`) is invalid and is ignored.
- The labels after `*.` must equal the hostname's labels after its first one, and the hostname has exactly one label more. So `*.shop.example` matches `api.shop.example`, but neither `shop.example` (no label for the `*`) nor `a.b.shop.example` (two labels).
- This problem adds one rule of its own: a wildcard name needs at least two labels after the `*`. `*.example` is ignored, so that one certificate cannot cover a whole top-level name. (RFC 9525 leaves protection against wildcards over public suffixes out of its scope; real clients use a list of public suffixes.)

The subject's common name (`CN=...`) is **never** used as a hostname, even when it looks like one (RFC 9525, section 2). Only `dnsNames` counts.

### Example 1

<!-- case: ex1 -->

The certificate is valid from 1000 through 5000 for two names. At 5000 it is still valid, at 5001 it has expired, and at 999 it is not yet valid. `api.shop.example` is not one of its names. An unknown id is reported first.

### Example 2

<!-- case: ex2 -->

`*.shop.example` covers one label in front of `shop.example`, in any case, but not two labels and not `shop.example` itself, which the second name covers. `evilshop.example` only ends with the same letters.

## Level 2: Building a chain

A server sends its certificate, usually with some others, and the client may know more, so the validator has an unordered pool of certificates and must assemble the chain itself.

- `addSignature(signerId, certId, valid)`: records the result of checking the signature on certificate `certId` with the public key of certificate `signerId`: `true` if it verifies, `false` if not. A later call for the same pair replaces the earlier result. A pair that was never recorded does not verify.
- `addTrustAnchor(certId)`: trusts the certificate `certId` as an anchor. Returns `true`, or `false` when the id is unknown or already an anchor.
- `buildChain(leafId)`: a chain from the leaf to a trust anchor, as the list of ids `[leafId, ..., anchorId]`, or `[]` when the leaf is unknown or there is none.

**Links.** Certificate `C` can be followed by certificate `P` in a chain when `P`'s subject is exactly `C`'s issuer **and** the signature of `P` on `C` was recorded as valid. A name alone is not enough: anyone can write a certificate with any issuer name, and only the signature shows who really issued it. A signature alone is not enough either.

**Chains.** A chain starts at the leaf, follows links, never uses a certificate twice, and **ends at the first trust anchor** it reaches. It holds at least one certificate besides that anchor, so a leaf that is itself a trust anchor has no chain, and `buildChain` returns `[]` for it. Among all chains, `buildChain` returns the one with the fewest certificates; among equally short ones, the one whose list of ids is smallest, compared id by id from the leaf. Several chains can exist when two CA certificates have the same subject, for example a CA that was **cross-signed** by two different roots.

The trust anchor's own signature, dates and other contents are not checked: it is trusted because it was configured, and only its name and key are used.

### Example 1

<!-- case: ex3 -->

The leaf was signed by the issuing CA, which was signed by the root, a trust anchor. The issuing CA's own chain is one link shorter. An unknown leaf has no chain.

### Example 2

<!-- case: ex4 -->

`int-a` and `int-b` both have the subject the leaf names as its issuer, but only `int-b`'s signature on the leaf verifies, so the chain goes through `int-b`. `stray` names an issuer that is in no certificate of the pool.

## Level 3: Constraints on issuers

Being in a chain is not enough: a certificate in the middle signs other certificates, and only some certificates are allowed to. If a client skipped this check, the owner of any ordinary site certificate could use its key to sign a certificate for a different site.

- `setConstraints(certId, isCa, pathLen, keyUsage)`: records two extensions of the certificate. *Basic constraints*: `isCa` says whether it is a CA, and `pathLen` is how many more non-self-issued intermediate certificates may follow it in a chain, `-1` for no limit. *Key usage*: the purposes its key may be used for, such as `keyCertSign` (signing certificates) and `digitalSignature`; `[]` means the extension is absent. A later call replaces the earlier values. Returns `false` for an unknown id, else `true`. A certificate for which this is never called has neither extension, so it is not a CA.
- `validatePath(path, hostname, now)`: validates the given chain `[leaf, ..., anchor]` (at least two ids) and returns `[reason, certId]` for the first problem found, or `["ok", ""]`.

The checks follow the path validation of RFC 5280, section 6.1, in this order:

1. **Structure**, over the whole list. First, a leaf that is itself a trust anchor gives `leaf-is-anchor`, with the leaf's id, before any other check: path validation needs at least one certificate besides the anchor, and an anchor is never checked, so a trusted leaf would skip its dates and revocation. Then an id that is not a known certificate gives `unknown-certificate` (the first such id from the leaf); a certificate that appears again gives `repeated-certificate` (the id at its second appearance, scanning from the leaf); a last id that is not a trust anchor gives `not-trusted`.
2. **Each certificate, from the one the anchor signed down to the leaf.** In RFC 5280 the path is these `n` certificates, without the anchor, which only provides the first issuer name and key. For each certificate, with the one before it (closer to the anchor) as its signer:
   1. `bad-signature`: the signer's signature on it is not recorded as valid.
   2. `not-yet-valid` or `expired`, as in level 1.
   3. `name-mismatch`: its issuer is not the signer's subject.
   4. Then, only for a certificate that is not the leaf (an **intermediate**):
      - `not-a-ca`: it is not a CA.
      - `path-too-long`: it is not self-issued (its subject and issuer differ) and the path's remaining length is 0. Otherwise, when it is not self-issued, the remaining length goes down by 1. The remaining length starts at `n`, the number of certificates in the path without the anchor.
      - Then, if its `pathLen` is not `-1` and is smaller than the remaining length, the remaining length becomes its `pathLen`.
      - `missing-key-cert-sign`: it has a key usage extension without `keyCertSign`.
3. **The hostname**, last: `hostname-mismatch` with the leaf's id when `matchedName(leaf, hostname)` is `""`.

The trust anchor's constraints are not checked either, and a self-issued intermediate (a CA's new certificate for its own key change, signed under its own name) does not count against any `pathLen`.

### Example 1

<!-- case: ex5 -->

Before `setConstraints`, `int` is not a CA, so it may not sign the leaf. Once it is a CA with `keyCertSign`, the path is valid. The hostname is checked only after every certificate passed.

### Example 2

<!-- case: ex6 -->

`int-1` has `pathLen` 0: no further intermediate may follow it, but `int-2` does. The remaining length starts at 3, becomes 2 after `int-1` and then 0 because of its `pathLen`, so `int-2` finds it at 0. With `pathLen` 1 the path is valid. At time 3000, `int-2` has expired, and that is found before the leaf's hostname is looked at.

## Level 4: Revocation and choosing a path

A CA can withdraw a certificate before it expires, for example when its private key was stolen, by publishing it in a **revocation list**. And because CAs cross-sign each other, a leaf often has several chains: a short one through an old intermediate that has expired, a longer one through a new root. A good validator tries the chains in a fixed order and accepts the first that passes, and it can say why it refused each of the others.

- `revoke(certId)`: records that the certificate is on a revocation list its issuer published. Returns `true`, or `false` when the id is unknown or already revoked.
- From now on, path validation checks revocation, right after the dates (step 2.2): `revoked`, with the certificate's id. As with every other check of step 2, the trust anchor is not checked: a revoked anchor still anchors. Revocation is part of path validation only; `checkLeaf` and `buildChain` do not look at it.
- `verify(leafId, hostname, now)`: tries every chain that `buildChain` considers, in the same order (fewest certificates first, then the smallest list of ids), and validates each with `validatePath`. It returns one row per chain tried, `[reason, certId, ...chain]`, and stops after the first `ok` row, whose `certId` is `""`. Before any chain is tried, an unknown leaf returns `[["unknown-certificate", leafId]]`, and a leaf that is itself a trust anchor returns `[["leaf-is-anchor", leafId]]`, whatever its dates. When no chain exists it returns `[["no-path", leafId]]`.

### Example 1

<!-- case: ex7 -->

At time 1500 the short chain through `issuing-a` is valid. At 3000, `issuing-a` has expired, so `verify` reports why and tries the longer chain through the bridge CA, which is valid.

### Example 2

<!-- case: ex8 -->

Once `int` is revoked, the only chain fails, and the row says which certificate is to blame. An unknown leaf, and a leaf with no chain at all, each get one row of their own.

## Constraints

- At most 200 calls per test, and at most 15 certificates.
- For any leaf, at most 100 chains as defined in level 2.
- `0 <= notBefore, notAfter, now <= 10^12`, and `-1 <= pathLen <= 10`.
- `dnsNames` holds at most 10 names, each made of ASCII letters, digits, `-`, `*` and single dots, with no dot at either end.
- `keyUsage` holds at most 9 names; `path` holds 2 to 16 ids.

## Follow-ups

- Real path building must also stop on huge pools and long loops. How would you bound the search, and which chains might you miss?
- RFC 5280 also checks name constraints, certificate policies and extended key usage. Which of them would you add next for a TLS server certificate, and where in the order of checks?
- Revocation lists can be large and stale. What does a client do when it cannot get a fresh answer, and what does each choice risk?
- An intermediate is missing from what the server sent, but the leaf says where to download it. Should the validator fetch it, and what would it have to check first?

## Hints

### Hint 1

Start with dates and names, which do not need any other certificate. Compare the dates with `<` and `>` so that both ends of the period count as valid. For names, split both sides on dots after lowercasing them, and compare the lists of labels.

### Hint 2

For a wildcard name, check its shape before anything else: the first label is exactly `*`, no other label contains `*`, and at least two labels follow. A name with the wrong shape never matches. Then the hostname must have one label more, and every label after the first must be equal.

### Hint 3

A chain is a path in a graph: from each certificate, the possible next ones are those whose subject equals its issuer and whose signature on it is recorded as valid. Keep the signatures in a map keyed by the pair of ids. A depth-first search that never revisits an id on the current path, and stops at a trust anchor, finds every chain.

### Hint 4

Collect every chain, then sort them by length and by their lists of ids. The first one is `buildChain`'s answer, and the whole sorted list is the order in which `verify` tries them.

### Hint 5

For `validatePath`, reverse the list so that you walk from the anchor towards the leaf, keeping the previous certificate as the signer. Keep the remaining length as a variable that starts at the number of certificates without the anchor. Return at the first failing check, in exactly the order of the statement; most mistakes are about checking things in another order, or checking the leaf or the anchor when only intermediates should be checked.
