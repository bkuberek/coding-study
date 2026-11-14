# Safe Redaction (Python): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | O(p * n) per call for p proposals and n characters | O(n + p) | default answer: place each proposal by its quote, merge what overlaps, add two patterns, and write the text once from the final spans |

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | Replace spans by labels | `Span` and `apply` in `redaction/spans.py`: the text is rebuilt from pieces |
| 2 | Believe only what the text confirms | `believed` and `nearest_occurrence` place a proposal by its quote; `merge` joins what overlaps (`redaction/trust.py`) |
| 3 | Catch what the model missed | `found_by_patterns` in `redaction/net.py`; its spans join the believed ones before the one merge |
| 4 | Measure it | `score` in `redaction/scoring.py`; `evaluate` reuses the spans `redact_safely` ends with |

## Approach: reference (Rebuild the text around spans that were placed by their quotes, merged, and joined by two patterns)

### Intuition

The redactor has one job and one enemy. The job is to leave no personal data in the text. The enemy is that it learns where the data is from something it cannot trust, and that a position is only meaningful in the text it was measured on.

So the design keeps three things apart. *Where the spans are* is decided first, on the original text, and never on a text that is changing: proposals are placed, patterns are run, and everything is merged into one list of non-overlapping spans. *What the text becomes* is decided last, and once: the new text is built left to right from copies of the stretches between the spans and the labels, so no offset ever has to be moved. And *how good it is* is a separate, pure function over two lists of spans.

The quote is what makes a proposal checkable. An offset is a claim about a place, and the quote is a claim about the content at that place; when the two disagree, the content is the one that can be found again. That is why a proposal is moved to its quote, not the other way round, and why a proposal whose quote is nowhere has nothing left to stand on and is dropped. The patterns exist because recall is what matters here: they recover the two kinds of data that have a shape and so can be found without a model, and they run on the original text for the same reason everything else does.

### Say it out loud

"I decide where the spans are before I touch the text. Each proposal is either right where it says, or moved to where its quote really is, nearest to what it claimed, or dropped. Then I add what two regular expressions find on the same original text, and merge it all: spans that share a character become one, with the label of the longest.

"Only then do I write. I build the result left to right: copy the text before the first span, write its label, copy up to the next one, and so on. I never replace inside the string, so the labels' lengths cannot throw off an offset, and I don't have to remember to go backwards.

"For the score I count matches on exact start, end and label, and I give recall the weight: F2 is five times the matches over five times the matches plus four times the misses plus the false alarms. Missing a span costs four times what a needless one does, because a missed email is a leak and a needless label is a nuisance."

### Algorithm

1. Place each proposal. If it lies in the text and cuts out its own quote, keep it. If not, and the quote is not empty and occurs in the text, move it to the occurrence closest to its `start` (the earlier on a tie), keeping its label. Otherwise drop it.
2. Run the email pattern and then the phone pattern on the original text, and turn every match into a span.
3. Put the placed proposals first and the pattern spans after them, then merge: sort by start and end; walk through, growing a group while the next span starts before the group's end; each group becomes one span from its earliest start to its latest end, labelled by its longest member, then the earliest start, then the earliest position in the list.
4. Write the text from the merged spans: copy, label, copy, label, and the tail.
5. To score, count the matches of the final spans against the gold spans with a counter, so each is used once, and apply the formulas, with the cases of an empty side given by the problem.

### Design

- `redaction/spans.py`: `Span`, and `apply`, the only code that builds the new text.
- `redaction/trust.py`: `nearest_occurrence`, `believed` (step 1) and `merge` (step 3). It knows nothing about regular expressions or scoring.
- `redaction/net.py`: the two patterns, as constants, and `found_by_patterns`.
- `redaction/scoring.py`: `score`, over two lists of spans.
- `redaction/redactor.py`: the class the grader drives. It turns the lists of the signature into `Span` and `Proposal` records, calls the pieces in order, and holds no rule of its own. `_safe` is the one place that says what `redact_safely` and `evaluate` both mean.
- `redaction/models.py` and `redaction/extractor.py`: the starter's, unchanged.

Not graded, and worth discussing:

- **Label conflicts.** Keeping the longest label is one policy. Another keeps the most specific, by a priority list (`EMAIL` over `PERSON`), or keeps both labels. The label never changes what is hidden, only what a reader is told.
- **Unplaceable proposals.** Dropping them is the safe choice for utility and the unsafe one for privacy: the words may be real personal data, misquoted. A production system would log them, count them, and measure how often the model's quotes fail.
- **Names.** The net covers shapes that have a regular form. Names have none, so a name the model misses stays in the text; the score is how you find out how often.
- **Corpus scores.** Adding up `tp`, `fp` and `fn` over many texts, then dividing, weights each span equally; averaging each text's score weights each text equally, and a short text with a missed address then counts as much as a long one with a hundred hits.

### Correctness

After merging, no two spans share a character, so `apply` can write each label once, and everything outside the spans is copied unchanged. A placed proposal covers the characters its quote really occupies, or the characters its own offsets cover when those cut out the quote, so a believed span never hides words the model did not name. Every match of either pattern is in the final list, as a span of its own or as part of the span it overlaps, so no pattern match survives in the output: a span that contains it replaces it, and nothing is hidden twice because the merge leaves no overlap.

`score` pairs each gold span with at most one equal chosen span and the reverse, so `tp <= min(|chosen|, |gold|)`, `fp` and `fn` are the remainders, and the formulas follow.

### Complexity

- Time: O(p * n) per call for p proposals and n characters — placing a proposal may scan the whole text for its quote; the patterns are linear in the text; the merge sorts the spans
- Space: O(n + p) — the new text and the lists of spans

### Trade-offs

Scanning for every occurrence of a quote is simple and linear per proposal, and is quadratic when the quote is a single character that occurs everywhere. An index from quote to positions, or a search that stops outward from the claimed `start` when the next occurrence cannot be closer, brings it down, at the price of code that most texts do not need.

Merging by union is generous: a long span proposed by mistake swallows what the patterns found inside it. The alternative, to trust the pattern over the model inside a span the model proposed, would prefer the finds that have a checkable shape, and it needs a rule for what a conflict means. The reference takes the side of hiding more.

### Pitfalls and edge cases

- **Moving text, moving offsets.** Replacing a span in a copy of the text and then using the next span's offset on the copy hides the wrong characters whenever a label is longer or shorter than its span (`ex2`, `h9`). Building from pieces, or going from the last span to the first, avoids it.
- **Replacing by text.** `str.replace("ana", ...)` hides every `ana`, when only some are spans (`h6`).
- **Characters, bytes and code points.** A Python `str` is indexed by code points, so `Café` is 4 and the emoji `😀` is 1. The extractor counts UTF-8 bytes, so after an accent or an emoji its offsets are too far right (`ex3`, `h23`), and the quote is how they are fixed.
- **Slices never complain.** `text[900:915]` is `""` and `text[-6:9]` is something. A range check has to be written (`h13`).
- **Overlap versus touching.** Spans that share a character merge, and spans that only touch do not (`h20`). A merge that tests `<=` instead of `<` joins `AdaLovelace` into one label.
- **Overlap is transitive.** A, B and C where A overlaps B and B overlaps C are one span, even though A and C do not touch (`h19`); a pairwise merge that is not repeated misses it.
- **The merged label.** Longest, then earliest start, then earliest given. The input order matters only on a tie, and an implementation that sorts first loses it (`h21`).
- **Quote ties.** Two occurrences equally far from the claimed start: the earlier (`h16`). Occurrences that overlap each other: `find` must advance by one, not by the quote's length (`h25`).
- **A pattern run on the redacted text.** Its offsets are the changed text's. Run both patterns on the original (`ex6`, `h30`).
- **Hiding twice.** A find that overlaps a proposal must merge with it. Hiding both gives `[PERSON][EMAIL]` for one address, or nested labels (`h31`, `h32`).
- **Digits are not always phones.** A date, an order number of 13 digits and a short code are not matched by the pattern, because of the 3-3-4 shape and the guards on both sides (`h29`).
- **Unicode.** `\w` in the email pattern matches `é`, so `josé@correo.es` is found whole (`h34`). The pattern for the domain does not, so a domain with an accent is not an email to it.
- **F1 is not F2.** Finding half of the spans with no mistake and finding all of them among as many mistakes have the same F1 and different F2 (`h46`).
- **The empty cases.** Nothing hidden has precision 1 and recall 0; nothing to hide but something hidden has precision 0 and recall 1; both empty is 1 for all (`h38`, `h39`, `h40`). A division by zero is the usual bug.
- **A span claimed twice.** It is right once and wrong once (`h42`).
