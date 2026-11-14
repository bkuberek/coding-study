# Grounded Memory Store: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| receipts-and-propagation | optimal | O(n log n) per call | O(n) | default answer; statuses are kept up to date by recomputing only what a change can reach |

Here `n` is the number of claims, citations, premises and source versions.

## How the design grows level by level

| Level | Change | What the store adds |
|-------|--------|---------------------|
| 1 | Claims with evidence | Receipts of texts, sources and claims by id, a citation per source with its receipt, all-or-nothing validation, and an index from each source to the claims that cite it |
| 2 | Drift detection | A history of receipts per source with the last position of each receipt in it; status computed from receipts, and the claims citing a changed source recomputed before and after |
| 3 | Re-verification | A refuted flag per citation, derived claims with an index from each claim to the claims resting on it, and recomputation of everything downstream in order of addition |
| 4 | Answering with trust | Word matching, a policy filter applied before the cut to `k`, evidence rendered with warnings, and a report over all claims and citations |

The early choice that carries everything is to compare receipts, never texts, and to treat a status as something derived from the receipts and refutations rather than as a flag that events set. Level 2 then needs no special case for a text that comes back, level 3 adds one more input to the same rule, and level 4 only reads the statuses.

## Approach: receipts-and-propagation (Compare receipts instead of texts and recompute only the claims downstream of a change in order of addition)

### Intuition

A claim is only as good as the text it was formed from, and a receipt names that text in 12 characters. Keeping the cited receipt with each citation turns "is this memory still grounded?" into a comparison of two short strings: the receipt the claim cites and the receipt of the source's current text. Nothing is decided by reading the texts again, which is what makes drift detection cheap and deterministic, and only `verify`, which stands for a checker, reads a text at all. Derived claims make the memory a graph: a change at a source reaches the claims that cite it, then the claims that rest on those, and so on. Since a premise always exists before the claims that rest on it, the order of addition is already a topological order, and recomputing the affected claims in that order needs no graph sort.

### Algorithm

1. `addSource`: refuse a known id; otherwise store the text, the history `[receipt]`, a map from each receipt to its last position in the history (its keys are the receipts of the texts the source has held), and an empty list of citing claims. Return the receipt.
2. `addClaim`: refuse a known id or an empty list. Build the citations in a new dictionary: refuse an unknown source, a source already in the dictionary, or a receipt that is not a key of the source's map of positions. Only when every pair passed, store the claim with its order of addition and add its id to the citing list of each source.
3. Status of a base claim: `contradicted` if a citation is refuted, else `stale` if a citation's receipt differs from its source's current receipt, else `trusted`. Status of a derived claim: the worst status of its premises, with `contradicted` read as `unsupported`. Each claim stores its status, computed when it is added.
4. `updateSource`: refuse an unknown id or a receipt equal to the current one. Otherwise set the text, append the receipt to the history, record its new last position, and refresh the claims citing the source (step 6).
5. `verify`: refuse a claim that is not a base claim citing the source. If the current text contains the phrase, set the citation's receipt to the current receipt and clear its refuted flag; otherwise set the flag. Refresh the claim (step 6).
6. Refresh: walk from the seed claims through the index of claims resting on each claim, with a visited set, to collect every affected claim. Sort them by order of addition and recompute each status from its citations or from its premises' stored statuses, which are already recomputed. Return the claims whose status changed, sorted by id.
7. `history`, `evidence`, `citing`, `staleClaims` and `dependents` read the stored data; `dependents` is the walk of step 6 without the seed. `drift` keeps the outdated citations, with `behind` equal to the last position in the history minus the last position of the cited receipt.
8. `recall`: split the query into words, keep the claims whose words contain them all and whose status the policy allows, sort by `(rank of status, id)`, and keep the first `k`. Render each citation as `sourceId@receipt`, marking outdated ones, or each premise by id, marking stale ones.
9. `report`: count the statuses, compute `trusted * 100 // claims` (or `n/a`), and scan every citation once for the set of drifted sources and the largest `behind`.

### Correctness

Status: the stored status of every claim equals the status the statement defines. It holds when a claim is added, since its status is computed then from current data. A status depends only on the claim's citations and on its premises' statuses, so a change at source `s` can alter only the claims citing `s` and, through premises, the claims resting on them, transitively; `verify` alters one citation, so it can alter only that claim and the claims resting on it. Step 6 recomputes exactly that set. A premise is added before the claims that rest on it, so it comes earlier in the order of addition: when a claim is recomputed, every premise of it is either unaffected, and its stored status is still right, or affected and already recomputed. By induction along that order, every recomputed status is right, and every status outside the set did not change.

Rows: a claim is listed when its status before the refresh differs from its status after it, which is the definition of a changed status. Claims outside the affected set cannot change, so none is missed.

Receipts and versions: a history entry is added exactly when the receipt changes, so a repeated text starts no version, and a text that comes back appends its receipt again. A citation's receipt is always in the history, because it was accepted as a key of the map or refreshed to the current receipt. The map holds the last position of each receipt, since every append overwrites it, so the number of entries after that position is the number of versions since the receipt was last current.

Recall: filtering by policy before the cut means the first `k` usable claims are returned; cutting first could return fewer although more usable claims match.

### Complexity

- Time: O(n log n) per call — `addSource`, `addClaim`, `addDerived`, `status` and `history` are linear in their own input; `updateSource` and `verify` touch only the affected claims and their citations and premises, then sort them by order and the changed rows by id; `dependents` walks the affected claims once and sorts them; `recall` matches every claim's words and sorts the usable ones; `report` scans every citation once, with `behind` read from the map of positions in constant time.
- Space: O(n) — the sources with their histories and maps of positions, the claims with their citations and premises, and the two indexes, each holding one entry per citation or premise.

### Trade-offs

- Comparing receipts instead of texts keeps drift detection independent of text length and of any model: a stale claim is found by a string comparison. The price is that any edit, even far from the passage a claim came from, makes it stale. Receipts of passages instead of whole documents would be more precise, at the cost of choosing passages and keeping them stable.
- Content addressing, as opposed to a version counter, makes a repeated save a no-op and a revert restore trust. A counter would mark every claim stale on a save that changed nothing, and would keep claims stale after a revert.
- Statuses are stored and refreshed incrementally. Recomputing every status on every call is simpler and gives the same answers, and is fine for a small memory; the incremental refresh keeps a change at one source proportional to what rests on it.
- Twelve hexadecimal characters are 48 bits, enough for the examples. A store that must not confuse two texts keeps the whole 256-bit digest; the standard allows a digest to be truncated to its leftmost bits and points to separate guidance for choosing the length.
- Refutations are sticky until a check passes. That keeps a contradicted claim visible even after its source reverts, which is the conservative choice; a store that trusts reverts would clear refutations whose text came back.
- Derived claims recover automatically when their premises do. That is right when the inference is mechanical, and too generous when a model made it: such a claim could be marked for a check of its own instead.

### Pitfalls and edge cases

- Level 1: hash the UTF-8 bytes of the text exactly as given, with no trimming, and keep 12 lowercase characters; equal texts in different sources share a receipt, but a claim may only cite a receipt of a text its own source has held. A second `addSource` with the same id changes nothing. Validate every citation before storing anything, so that a refused claim leaves no trace in `citing` and its id stays free. Duplicate sources, unknown sources and an empty list are refused. Evidence is sorted by source id, not in the order given, and ids sort by character codes, so `freeze-2` comes before `freeze_2`.
- Level 2: a repeated text starts no version. A text that comes back appends its receipt again and makes the claims citing it trusted again, so staleness must not be a flag that only goes one way. One outdated citation makes a claim stale. Only claims whose status changed are listed: a claim that was already stale is not listed again. A receipt of an earlier text is still accepted by `addClaim`, and a receipt the source never held is not. `behind` counts from the last time the cited receipt was current, not the first. Stale claims keep their status and their evidence.
- Level 3: the phrase is matched exactly, case included, against the current text, never against the text the citation was formed from. A successful check refreshes only the citation it names, and clears its refutation even when nothing had drifted; a failed check keeps the old receipt. A refutation survives source updates, including a revert. A refuted citation outranks an outdated one. A contradicted premise makes a claim unsupported, not contradicted, and an unsupported or stale premise passes on unchanged; propagation goes all the way down, and through a diamond each claim is listed once. `dependents` excludes the claim itself. A derived claim cannot be verified, and `addDerived` refuses unknown, repeated or missing premises.
- Level 4: words are runs of lowercase letters and digits, so `rate` does not match `separate` and `rate-limit` holds two words; the query is lowercased too, and a query with no words matches everything. Filter by policy before keeping `k`, and put trusted claims before stale ones. Unsupported and contradicted claims are never returned. Premises are sorted in the row, whatever order they were given in. The share is rounded down, counts only trusted claims, and is `n/a` for an empty memory. Drifted sources count sources, not citations, and `max behind` uses the same `behind` as `drift`.

### Language notes

- Python: `hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]` is the receipt. Dictionaries keep insertion order, which gives each claim's order of addition for free, but an explicit counter states the intent. `sorted` on strings compares code points, which is the order the statement asks for with ASCII ids. `set.issubset`, or `<=` on sets, tests that a claim's words contain the query's.
- TypeScript: `createHash("sha256").update(text, "utf8").digest("hex").slice(0, 12)` from `node:crypto` hashes the UTF-8 bytes; passing the string without an encoding also uses UTF-8, but `"latin1"` or `"binary"` would keep only the low byte of each code unit. Ids compare with `<` and `>`, not `localeCompare`, which would order `-` and `_` by locale rules. `Math.floor(trusted * 100 / claims)` is exact for these small integers. `Map` and `Set` keep insertion order and have no inherited keys, so an id such as `constructor` is safe.

## Further reading

- J. Doyle, "A truth maintenance system", *Artificial Intelligence* 12(3), 1979, pp. 231-272, [doi:10.1016/0004-3702(79)90008-0](https://doi.org/10.1016/0004-3702(79)90008-0): a subsystem that keeps track of why a program holds each of its beliefs, so that the beliefs can be revised when new findings undermine the assumptions behind them, and that introduces dependency-directed backtracking. Derived claims and their propagation echo the idea in a much simpler form.
- NIST, FIPS 180-4, [*Secure Hash Standard (SHS)*](https://doi.org/10.6028/NIST.FIPS.180-4), August 2015: the standard that defines SHA-256, which notes that altering a message almost certainly changes its digest. Its Section 7 permits a shorter digest taken from the leftmost bits of a longer one, which is what a 12-character receipt is.
- R. Fielding, M. Nottingham and J. Reschke (editors), [RFC 9110: *HTTP Semantics*](https://www.rfc-editor.org/rfc/rfc9110), June 2022: Section 8.8.1 explains strong validators, metadata whose value changes with every change to the data it describes; Section 8.8.3 covers the `ETag` field that carries one, and Section 13.1.2 the `If-None-Match` field, which makes a request depend on entity tags. A receipt does a strong validator's job for a claim's evidence.
- W3C, [*PROV-DM: The PROV Data Model*](https://www.w3.org/TR/prov-dm/), W3C Recommendation, 30 April 2013: a model for recording where data came from, who and what took part in producing it, which things were derived from which, and revisions, derivations whose result is a new version of an original.
- T. Gao, H. Yen, J. Yu and D. Chen, "Enabling Large Language Models to Generate Text with Citations", EMNLP 2023, [arXiv:2305.14627](https://arxiv.org/abs/2305.14627): has models cite sources for what they write, so that their statements can be checked, and finds that on one of its datasets even the strongest models fall short of full citation support about half the time.
