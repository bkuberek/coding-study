# Grounded Memory Store

## Statement

Build `GroundedMemory`, the long-term memory of an AI agent that knows where each of its memories came from. The agent reads documents, such as a page of API docs or a pricing table, and remembers short statements it learned from them. Documents change after the agent has read them, and a memory that was true of the old text may be false of the new one. A memory that cannot say what it was based on can only be trusted blindly or thrown away. This store keeps, with every memory, a receipt of the exact text it was based on, so that it can always tell which memories still rest on the current documents.

The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**Sources and claims.** A **source** is a document the agent can read, with an id and a text. A **claim** is a statement the agent remembers, with an id, a text and its **citations**: each citation names a source and the receipt of the text the agent read there when it formed the claim.

**Receipts.** The **receipt** of a text is the first 12 characters of the SHA-256 digest of the text's UTF-8 bytes, written in lowercase hexadecimal (`0-9` and `a-f`). A hash function such as SHA-256 turns any text into a fixed-size fingerprint: the same text always gives the same receipt, whichever source holds it, and a change of a single character almost certainly gives an unrelated one. You do not need to know how SHA-256 works inside: in Python the receipt is `hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]`, and in TypeScript `createHash("sha256").update(text, "utf8").digest("hex").slice(0, 12)`, with `createHash` from `node:crypto`. The text is hashed exactly as given: no spaces are removed, no case is changed, and `é` is 2 bytes. The receipt of the empty text is `e3b0c44298fc`. Twelve characters keep the examples readable, and no two texts in the tests share a receipt.

Aim to finish in 90 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 25, level 2 by 45, level 3 by 70 and level 4 by 85, keeping the last minutes for a final run.

## Input

- `GroundedMemory()`: creates an empty memory.
- Source ids and claim ids are 1 to 20 characters from `a` to `z`, `0` to `9`, `-` and `_`. Sources and claims have separate ids: a claim may have the id of a source.
- A source's text is 0 to 1000 characters of any text (well-formed Unicode: no lone surrogates). A claim's text is 1 to 200 printable ASCII characters (codes 32 to 126).
- Each level's section describes the methods it adds and their parameters.

## Output

Statuses are lowercase words, such as `trusted`. Lists of ids, and rows that start with an id, are sorted by id unless a method says otherwise. Ids are compared by the numeric values of their characters, so `-` comes before the digits, which come before `_`, which comes before the letters. Numbers inside rows are written in decimal as text. An id that names nothing gets the empty answer: `""` for text and `[]` for a list.

## Level 1: Claims with evidence

- `addSource(sourceId, text)`: adds a source with `text` and returns the receipt of `text`. If `sourceId` is already a source, nothing changes and the answer is `""`: a source keeps the text it was added with.
- `addClaim(claimId, text, citations)`: adds a claim. `citations` is a list of pairs `[sourceId, receipt]`. The claim is stored, and the answer is `true`, when all of these hold:
  - `claimId` is not already a claim;
  - `citations` has at least one pair;
  - every `sourceId` is a source, and no source appears in two pairs;
  - every receipt is the receipt of a text that its source has held (here, the text it was added with).

  Otherwise the answer is `false` and nothing is stored: a refused claim leaves no trace, and its id stays free.
- `status(claimId)`: the claim's status, or `""` when `claimId` is not a claim.
- `evidence(claimId)`: the claim's citations, as rows `[sourceId, receipt]` sorted by source id.
- `citing(sourceId)`: the ids of the claims that cite the source, sorted.

**Status.** A citation is **current** when its receipt is the receipt of its source's current text. A claim whose citations are all current is `trusted`. At this level every claim is trusted, since a source keeps its text.

### Example 1

<!-- case: ex1 -->

Each `addSource` returns the receipt of its text. `rate` cites `limits` with the receipt that `addSource` returned, and `cost` cites both sources; its evidence comes back sorted by source id, whatever order the citations were given in. Both claims cite `limits`, and only `cost` cites `pricing`. An id that is not a claim has no status and no evidence.

### Example 2

<!-- case: ex2 -->

The second `addSource` of `owners` is refused, so `owners` keeps its first text, and `typo` is refused: it cites the receipt of a text that `owners` never held. The second `owner` reuses an id, `guess` cites a source that does not exist, `twice` cites the same source twice and `bare` cites nothing, so all four are refused. Refused claims leave no trace: only `owner` cites `owners`.

## Level 2: Drift detection

Documents get edited. This level lets a source change and tells which claims still rest on its current text.

- `updateSource(sourceId, text)`: gives the source a new text. When `sourceId` is not a source, or `text` has the receipt of the source's current text, nothing changes and the answer is `[]`. Otherwise `text` becomes the source's current text, and its receipt starts a new **version** of the source. The answer lists the claims whose status changed, as rows `[claimId, before, after]` sorted by claim id, or `[]` when no status changed.
- `history(sourceId)`: the receipts of the source's versions, oldest first: one for `addSource`, then one for each `updateSource` that started a version. A text that comes back gets its receipt again, so a source that went from text A to B and back to A has the history `[A, B, A]`, each written as its receipt.
- `drift(claimId)`: the claim's outdated citations (below), as rows `[sourceId, citedReceipt, currentReceipt, behind]` sorted by source id, where `currentReceipt` is the receipt of the source's current text and `behind`, written as text, is the number of versions the source has had since the cited receipt was last current: the number of entries of `history(sourceId)` after the last entry equal to `citedReceipt`.
- `staleClaims()`: the ids of the stale claims, sorted.

**Status.** A citation that is not current is **outdated**. A claim is `trusted` when all its citations are current, and `stale` when at least one is outdated. Status depends only on receipts: no text is compared and no model is asked. A source that goes back to the text that a claim cites makes that citation current again. Stale claims are kept, with their evidence: nothing is deleted. `addClaim` accepts the receipt of any text the source has held, so a claim formed from an earlier version is accepted, and it is stale from the start.

### Example 1

<!-- case: ex3 -->

`limits` changes, so its receipt changes, and both claims that cite it become stale. `cost` is stale although its citation of `pricing` is current: one outdated citation is enough. Its drift shows the receipt it cited, the current one, and that `limits` is 1 version past it. When `pricing` changes, only `plan` changes status, since `cost` was already stale. The evidence of a stale claim still names the receipt it was formed from.

### Example 2

<!-- case: ex4 -->

Updating `limits` with the text it already has starts no version. After the change to 60 requests, `late` cites the receipt of the first text, which `limits` has held, so it is accepted, stale from the start. When the first text comes back, its receipt comes back too: `rate` and `late` are trusted again, and `new`, which cites the second text, is stale, 1 version behind. A source that does not exist cannot be updated.

## Level 3: Re-verification

A stale claim may still be true: an edit elsewhere in a document changes its receipt. This level checks a claim against the current text, which either refreshes its evidence or contradicts it, and lets claims rest on other claims, so that a contradiction reaches everything built on it.

- `addDerived(claimId, text, premises)`: adds a **derived claim**, one that rests on other claims, its **premises**, instead of on sources. It is stored, and the answer is `true`, when `claimId` is not already a claim, `premises` has at least one id, every premise is a claim and no premise appears twice. Otherwise the answer is `false` and nothing is stored. The claims added by `addClaim` are **base claims**. A derived claim has no citations: `evidence` and `drift` answer `[]` for it, and `citing` never lists it. A premise is always added before the claims that rest on it, so no claim rests on itself.
- `verify(claimId, sourceId, phrase)`: checks one citation of a base claim against the source's current text. The check stands for a checker, a model or a person, that reads the text: the citation **holds** when the current text contains `phrase` exactly, as a substring with its case and spaces. When it holds, the citation's receipt becomes the receipt of the current text, which refreshes the evidence, and the citation is no longer refuted. Otherwise the citation is **refuted** and keeps its receipt. The answer lists the claims whose status changed, as `updateSource` does. When `claimId` is not a base claim that cites `sourceId`, nothing changes and the answer is `[]`.
- `dependents(claimId)`: the ids of every claim that rests on `claimId`, directly or through other derived claims, each once, sorted.

A refuted citation stays refuted until a `verify` of the same claim and source holds. `updateSource` does not change it, even when the text comes back to the one the citation was formed from.

**Status.** There are four statuses, from best to worst: `trusted`, `stale`, `unsupported` and `contradicted`.

- A base claim is `contradicted` when one of its citations is refuted, else `stale` when one is outdated, else `trusted`.
- A derived claim has the worst status among its premises, except that a contradicted premise counts as `unsupported`. So it is `trusted` when every premise is trusted, `stale` when the worst premise is stale, and `unsupported` when a premise is unsupported or contradicted.

`updateSource` and `verify` list every claim whose status changed, derived claims included, however far down they rest.

### Example 1

<!-- case: ex5 -->

`hourly` rests on `rate` and `batch` on `hourly`, so both depend on `rate`. When `limits` changes, all three become stale: `rate` through its citation, the others through their premises. Verifying `rate` fails, since `100 requests per minute` is no longer in the text: `rate` is contradicted, and the claims that rest on it are unsupported. A derived claim has no evidence, and its id cannot be reused.

### Example 2

<!-- case: ex6 -->

The new text of `limits` still contains `100 requests per minute`, so `verify` refreshes the receipt of `rate`, and `rate` and `value` are trusted again. The match is exact: `20 Dollars` is not in the text of `pricing`, so `plan` is contradicted and `value` unsupported, until `20 dollars` is found. A derived claim cites no source, so there is nothing of it to verify.

## Level 4: Answering with trust

An agent answering a question should use only the memories that still hold, and say how far to trust them. This level answers a query under a policy and reports the state of the whole memory.

- `recall(query, policy, k)`: the claims an answer may use, as rows (below).
- `report()`: a summary, as the lines described below.

**Matching.** A **word** is a longest run of characters from `a` to `z` and `0` to `9`, once the letters `A` to `Z` are written in lowercase; every other character separates words. A claim matches the query when every word of the query is a word of the claim's text. A query with no words matches every claim.

**Policy.** Under `strict`, only `trusted` claims are usable; under `lenient`, `trusted` and `stale` claims are. Unsupported and contradicted claims are never usable.

**Answer.** Take the matching usable claims, put the trusted ones before the stale ones, each group sorted by id, and return the first `k` (all of them when there are fewer). Each row is `[claimId, status, text, ...]`, followed by the claim's evidence:

- for a base claim, one entry per citation, sorted by source id: `sourceId@receipt`, followed by ` (outdated)` when the citation is outdated;
- for a derived claim, one entry per premise, sorted: the premise's id, followed by ` (stale)` when the premise is stale.

**Report.** These 9 lines, in order:

```text
claims: <the number of claims>
trusted: <the number of trusted claims>
stale: <the number of stale claims>
unsupported: <the number of unsupported claims>
contradicted: <the number of contradicted claims>
supported: <the share of the claims that are trusted, in percent, rounded down, then %>
sources: <the number of sources>
drifted sources: <the number of sources that some claim cites with an outdated receipt>
max behind: <the largest behind of drift() over every outdated citation, 0 when there is none>
```

Each `<...>` is replaced by its value. With 2 trusted claims out of 3, the share line is `supported: 66%`. With no claims, it is `supported: n/a`.

### Example 1

<!-- case: ex7 -->

After `limits` changes, `rate` is verified and trusted with a fresh receipt, while `burst` stays stale. Under `strict` only `rate` is usable; `lenient` adds `burst` after it, with a warning on its outdated citation. The empty query matches every claim, and `k = 2` keeps the first two trusted claims by id. Two claims of three are trusted, 66% rounded down, and one source is cited with an outdated receipt. Then `spread` is derived from `burst`; it is stale from the start, since its premise is, and `lenient` returns it after `burst`, with its premise marked ` (stale)`.

### Example 2

<!-- case: ex8 -->

An empty memory has no share to report. Once `rate` is contradicted, `value` is unsupported, and the change to `pricing` makes `plan` stale. The query `pro plan` matches `plan` and `value`, but only `plan` is usable, and only under `lenient`. Both sources are now cited with outdated receipts.

## Constraints

- At most 300 calls per test.
- At most 5 pairs in `citations` and at most 5 ids in `premises`; each pair holds exactly two strings, and each receipt in it is 1 to 64 letters and digits.
- `phrase` is 1 to 100 characters of well-formed Unicode text. `query` is 0 to 100 printable ASCII characters, `policy` is `strict` or `lenient`, and `k` is from 1 to 50.

## Follow-ups

- A receipt here has 48 bits. Roughly how many distinct texts can a memory hold before two of them are likely to share a receipt, and what would you store in a real system?
- A whole-document receipt goes stale when any part of the document changes. How would you cite the passage a claim came from, so that an edit elsewhere leaves the claim trusted?
- The checker here is a phrase match. With a model as the checker, the same check can give different answers. What would you record with each verdict so that it can be audited and repeated?
- Contradicted and stale claims are kept. When should a memory forget them, and how does that square with a user's request to delete what the agent knows about them?
- A derived claim becomes trusted again as soon as its premises are. When is that right, and when should the inference itself be checked again?
- Two agents share one memory: one updates a source while the other forms a claim from the old text. Which of the rules above already handle that, and what is missing?

## Hints

### Hint 1

Two dictionaries carry level 1: one from source id to the source (its text and its receipt), and one from claim id to the claim (its text, and a dictionary from source id to the receipt it cites). For `addClaim`, check every rule first, and store the claim, and add its id to a third dictionary from source id to the claims that cite it, only when they all pass. Storing as you go is how a refused claim ends up listed by `citing`.

### Hint 2

Keep, for each source, the list of its receipts (its history) and a set of them. Do not store `stale` as a flag that a change sets: compute a claim's status from its citations and the current receipts, and a text that comes back makes its claims trusted again with no extra code. For the rows of `updateSource`, compare the status of each claim that cites the source before and after the change.

### Hint 3

For `behind`, walk the history from its end until you meet the cited receipt. Starting from the front finds the first time the text was current, which is wrong once a text has come back.

### Hint 4

Keep a dictionary from each claim to the claims that rest on it directly. `dependents` is a walk from a claim with a set of visited ids, since two paths can lead to the same claim. Since premises are always added first, the claims in their order of addition are already in an order where every premise comes before the claims that rest on it: recompute the statuses of the affected claims in that order, and each one reads statuses of its premises that are already up to date.

### Hint 5

Filter by policy first, then sort, then keep the first `k`. Keeping `k` first and dropping the stale ones afterwards returns fewer answers than asked for although usable ones exist. For the share, use integers: `trusted * 100 // claims`.
