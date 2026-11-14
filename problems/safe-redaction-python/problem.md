# Safe Redaction (Python)

## Statement

Before a text is stored, shown to someone else or sent to another system, the personal data in it has to go: email addresses, phone numbers, names. A model can find them. It reads the text and answers with *spans*, such as "characters 12 up to 27 are an `EMAIL`". Your `Redactor` takes those spans and writes the text again with each span replaced by its label, so `Mail ana@example.com` becomes `Mail [EMAIL]`.

That sounds like a single line of Python, and level 1 is close to that. The catch is in two places. First, a span is a position, and positions move: once you replace `ana@example.com` by the shorter `[EMAIL]`, every position after it points at the wrong place, so the order in which you do the work matters. Second, the model is not reliable. Its positions are sometimes wrong, the same words come back twice, and it misses things. A wrong answer here is not a harmless one: a missed email is a leak, while a hidden word that did not need hiding only makes the text a little harder to read. Most of the work is making the redactor safe when its input is wrong, and then measuring how safe it is.

The four levels are: hide spans that are right; check spans against the text and repair or drop the ones that are wrong; add two patterns that catch the emails and phone numbers the model missed; and score the whole thing against the answers it should have given, with a measure that cares more about what was missed than about what was hidden for nothing. Nothing here calls a real model: the starter has a small fixed-rule stand-in for one, which is wrong in the ways models are.

## Input

Every method takes the text and the spans as plain lists of the same length, one entry for each span `i`:

| Argument | Meaning |
|----------|---------|
| `text` | The text, a string |
| `starts[i]` | Where span `i` begins, a position in `text` counted from 0 |
| `ends[i]` | Where it stops: the span covers the characters from `starts[i]` up to, and not including, `ends[i]`, as the slice `text[starts[i]:ends[i]]` does |
| `labels[i]` | What span `i` is: `EMAIL`, `PHONE`, `PERSON`, or any other non-empty word |
| `quotes[i]` | From level 2 on: the text the model says it saw at that place. It may not be what is really there |

A position counts characters, as Python's `str` does, not bytes: in `Café ana`, `ana` begins at 5.

## Output

A method that redacts returns the new text. A method that scores returns `[precision, recall, f2]`, three floats from 0 to 1, compared with a small tolerance.

In the new text, each span that is hidden is replaced by `[` + its label + `]`, written exactly as the label was given: `[EMAIL]`, `[id_number]`. Everything outside the hidden spans stays exactly as it was.

## Project

`cstudy start` copies a small Python project into `projects/safe-redaction-python/` in your workspace, and you solve the problem there, in as many files as you like:

- `redaction/redactor.py`: the class `Redactor`, with level 1's method raising `NotImplementedError`.
- `redaction/models.py`: `Proposal`, a record with `start`, `end`, `label` and `quote`.
- `redaction/extractor.py`: `propose(text)`, a stand-in for the model with fixed rules. It is deliberately unreliable: its docstring lists how, and `tests/test_extractor.py` shows some of it. The graded cases hand your methods plain lists, so `Redactor` never calls it; your own tests can.
- `tests/conftest.py`: a `redactor` fixture for your own tests.
- `tests/test_level_<n>.py`: the examples of each open level as pytest tests, written when the level opens and never rewritten. Edit them, and add your own test files next to them.
- `README.md`, and `pyproject.toml` with the pytest, pyright and ruff settings.

The contract: `Redactor` stays in `redaction/redactor.py` and takes no constructor arguments, and every method keeps the name and parameters its level gives. Each level starts with a line naming the methods it adds.

`cstudy test safe-redaction-python` runs your tests, and so does `.venv/bin/pytest` in the project folder; either run is feedback only. `cstudy submit safe-redaction-python` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again, so a change for a new level must keep their rules.

## Level 1: Hide the spans

- `redact(text, starts, ends, labels)`: returns `text` with every span replaced by its label in brackets. At this level every span is right: `0 <= start < end <= len(text)`, and no two spans share a character. They may be given in any order, and two spans may touch (one ends where the next begins). No spans, or an empty text, is fine.

The one idea to take away: **replacing changes lengths, and a position only means something in the text it was measured on.** There are two ways to keep your positions valid. Replace from the last span to the first, so that nothing before the span you are working on has changed yet; or never change the text at all, and build the new one from pieces: the text between the spans, copied, and each label, in order. Replacing the words themselves with `str.replace` is not a way: the same words can occur more than once, and only some of them may be spans.

### Example 1

<!-- case: ex1 -->

An email and a phone number, each replaced by its label. The label `[EMAIL]` is shorter than `ana@example.com`, so the number after it would point too far right in the changed text.

### Example 2

<!-- case: ex2 -->

Here both labels are longer than the words they replace, and the second span has to land on `Bo`, not on whatever is at that position after the first change.

## Level 2: Do not trust the extractor

- `redact_proposed(text, starts, ends, labels, quotes)`: the spans are now *proposals* from the model, and each comes with the `quote` the model says it saw. Redact what can be believed.

Step 1, **place** each proposal:

1. If `0 <= start < end <= len(text)` and `text[start:end] == quote`, the proposal is right as it is.
2. Otherwise, if `quote` is not empty and occurs in `text`, the proposal is moved to where the quote really is: the occurrence whose start is closest to the proposal's `start`, the earlier of two that are equally close. Its span is that occurrence, from its start for `len(quote)` characters, and its label is the proposal's.
3. Otherwise, nothing can be said about where it is, and the proposal is dropped.

Occurrences of a quote may overlap each other (`aa` in `aaaa` occurs at 0, 1 and 2).

Step 2, **merge**: spans that share at least one character become one span, from the earliest start to the latest end of the group. Spans that only touch stay separate. Overlap is transitive: if A overlaps B and B overlaps C, the three are one span, even if A and C do not touch. A merged span takes the label of the longest span in its group; among spans of equal length the one that starts first; among those, the one that came first in the lists.

Step 3: write the text as level 1 does, with the merged spans. Proposals that cannot be placed leave their words in the text, and no proposals leave the text as it was.

### Example 1

<!-- case: ex3 -->

The extractor from the starter counts bytes. The `é` takes two, so every proposal after it is one place too far to the right, and cutting `text[start:end]` would hide the wrong characters. The quote is what tells where the email really is.

### Example 2

<!-- case: ex4 -->

`Hopper` is proposed twice, once on its own and once inside `Grace Hopper`, so those two merge into one. The extractor also cut the email at its first dot, so the proposal for `ana@mail.example` covers less than the whole address, and `.com` is left. Level 3 fixes that.

## Level 3: A safety net

- `redact_safely(text, starts, ends, labels, quotes)`: everything `redact_proposed` does, and a net under it. Two patterns find the emails and phone numbers the model missed or cut short, and their finds join the proposals before the merge.

The patterns, in Python's regular expression syntax, used exactly as written, on the original `text`:

```python
EMAIL = r"[\w.%+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}"
PHONE = r"(?<![\w+])(?:\+?[0-9]{1,3}[ .-])?(?:\([0-9]{3}\)|[0-9]{3})[ .-]?[0-9]{3}[ .-]?[0-9]{4}(?!\w)"
```

In words: an email is one or more letters, digits or `_ . % + -` before an `@`, then a domain of dot-separated parts with a last part of two or more letters, and it stops before a final full stop. A phone number is ten digits, grouped 3-3-4 with an optional separator of a space, a dot or a hyphen between the groups, an optional area code in brackets, and an optional country code with a `+` or a separator, and it is not a part of a longer run of letters or digits.

The rule: find every match of `EMAIL` in the text, in order, as spans labelled `EMAIL`, then every match of `PHONE`, as spans labelled `PHONE`. Add them to the believed proposals of level 2, after them, and merge all of it by the level 2 rule. Nothing is hidden twice: a find that lies inside, or overlaps, a span the model proposed becomes one span with it, so there is never a `[EMAIL]` inside a `[PERSON]`. When a proposal and a find cover exactly the same characters, the label is the proposal's, since it came first.

### Example 1

<!-- case: ex5 -->

The extractor never sees the dotted phone number, and reads `ana+news@x.io` as `news@x.io`, because it does not know `+`. The net finds the whole of both.

### Example 2

<!-- case: ex6 -->

The extractor cuts `ada@lab.example.com` at `lab.example`. The net finds all of it, the two overlap, and they become one span with one label.

## Level 4: Score it

How safe is the redactor? Compare the spans it hides with the spans that should have been hidden, called the gold spans. Two methods:

- `score(starts, ends, labels, gold_starts, gold_ends, gold_labels)`: compares one list of spans with the gold list and returns `[precision, recall, f2]`.
- `evaluate(text, starts, ends, labels, quotes, gold_starts, gold_ends, gold_labels)`: takes the model's proposals as `redact_safely` does, works out the spans that `redact_safely` would hide, and returns the `score` of those against the gold spans.

**Matching.** A span matches a gold span when its start, its end and its label are all equal. There is no credit for a close one: a span one character short, or with another label, is both a mistake and a miss. A span matches at most one gold span, and a gold span at most one span. Where the same span is given twice and the gold has it once, one is right and the other is a mistake. Let `tp` be the number of matches, `fp` the spans that match nothing, and `fn` the gold spans that nothing matches.

**The numbers.**

- `precision = tp / (tp + fp)`: of what was hidden, how much needed hiding. It is 1 when nothing was hidden.
- `recall = tp / (tp + fn)`: of what needed hiding, how much was hidden. It is 1 when there was nothing to hide.
- `f2 = 5 * tp / (5 * tp + 4 * fn + fp)`: the two combined so that recall counts more. When all of `tp`, `fn` and `fp` are 0, it is 1.

That `f2` is the F-measure with a weight of 2 on recall: `5 * P * R / (4 * P + R)`. A missed span costs it 4 times what a needless one does.

**Why recall.** The two kinds of mistake are not alike. A needless `[PERSON]` where the text said "Rome" costs a reader one word. A missed email address leaves a person's data in a text that will be stored, shared or sent on, and it cannot be taken back. A redactor that hides everything has perfect recall and no use, so precision still counts, which is why the score is not recall alone. But the F1 score, which weighs the two equally, would rate a redactor that finds half of the addresses without a single mistake above one that finds all of them and hides a few words too many. F2 rates them the other way round.

### Example 1

<!-- case: ex7 -->

Two of the three spans to find were hidden, and nothing else was: precision 1, recall 2/3, and `f2 = 10 / 14`.

### Example 2

<!-- case: ex8 -->

The same text that the extractor gets wrong in three ways. After placing, merging and the net, the spans match the gold spans exactly, so all three scores are 1.

## Constraints

- `text` has at most 100,000 characters, and a call has at most 1,000 spans or proposals.
- At level 1 every span is right, as described. From level 2 on, `starts` and `ends` may be any integers, negative or far past the end of the text, and `quotes` any strings, empty ones included.
- All lists of one call have the same length.
- Labels are non-empty and contain no brackets.
- The patterns of level 3 are the only ones: the graded cases do not ask for names or other kinds of personal data to be found by pattern.

## Follow-ups

- Two spans of different labels overlap: one wins here, by length. What would you lose by keeping both, as in `[EMAIL|PERSON]`, and what by keeping the first?
- A proposal that cannot be placed is dropped. Its words may be exactly the personal data the model found, only misquoted. What would happen if you hid the characters at its offsets anyway, and what would you log?
- The patterns are tuned to catch a lot. What do they catch that is not personal data, and which of those mistakes does F2 punish least? What would a pattern for a national id number cost in false alarms?
- Redacting names does not remove a person: "the only dentist in a village of 300" says who it is. What would a measure of that look like?
- Over a corpus of many texts, do you add up `tp`, `fp` and `fn` over all texts first (micro-averaging), or average each text's score (macro-averaging)? Which one hides a text that leaks everything?
- A model gives each span a confidence. How would you choose the threshold below which a proposal is ignored, and which of precision and recall moves when you raise it?
- When the redacted text goes to a language model, would you rather it saw `[PERSON]` or `[PERSON_1]`, `[PERSON_2]`? What does the second let you do afterwards?

## Hints

### Hint 1

A span is just two numbers, where it starts and where it stops. In Python `text[start:end]` is the text it covers, and `text[:start] + "[EMAIL]" + text[end:]` is the text with that span replaced. Get this working for one span before you think about several.

### Hint 2

The trouble with several spans: after the first replacement the text has a different length, so the numbers of the other spans no longer point at the same words. Two ways out. Sort the spans and work from the last to the first, so that the part of the text before the span you are replacing has not changed yet. Or leave `text` alone and build a new string from pieces: the stretch of `text` before the first span, its label, the stretch up to the next span, its label, and so on, then what is left. Either way, sort the spans by start first, because the lists come in any order.

### Hint 3

Level 2 is two small questions asked of each proposal in turn, and each is easier as a function of its own. "Is it where it says?" is `text[start:end] == quote`, guarded by a check that the numbers are in range, because a slice never complains about a number that is too big. "Where is it really?" is a loop with `text.find(quote, position)` that moves one character after each find, so that overlapping occurrences are seen too.

### Hint 4

To merge, sort the spans by start. Walk through them keeping the end of the group you are in. If the next span starts before that end, it overlaps: the group's end becomes the larger of the two ends. If it starts at that end or later, the group is finished and a new one begins. Remember each group's members, so that you can pick the label: the longest member, then the one that starts first, then the one that came first in the lists. Sorting loses the order they came in, so note it before you sort.

### Hint 5

Do not redact a second time. The net is not a second pass over the redacted text, whose positions have all moved: run the two patterns with `re.finditer` on the original text, turn each match into a span with `match.start()` and `match.end()`, put those spans in the same list as the believed proposals, and merge once. A find that overlaps a proposal then simply joins it.

### Hint 6

Count first: `tp`, `fp`, `fn`. For matching, a `collections.Counter` of the spans you chose (as tuples of start, end and label) lets you take one off for each gold span that is in it, and that handles a span given twice. Write `f2` with integers, `5 * tp / (5 * tp + 4 * fn + fp)`, and check the case where all three are 0 before dividing.

### Hint 7

`evaluate` needs the spans that `redact_safely` ends up hiding, and a method that only returns text does not give you those. Split `redact_safely` into a function that returns the final spans and a function that writes the text from spans, and let `evaluate` use the first.
