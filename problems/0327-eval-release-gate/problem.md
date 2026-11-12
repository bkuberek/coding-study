# Eval Release Gate

## Statement

A team changes the prompt of its assistant, or swaps the model behind it. Did the change make the assistant better, worse, or just different? Looking at a few answers by hand is not an answer. The usual practice is an **eval**: a fixed list of test questions (a **golden set**), a **run** of the old version and of the new one over all of them, and a set of checks on what came back. The checks end in one decision, ship or do not ship.

Build `ReleaseGate`, the part that takes the runs and makes the decision. It works in four layers, one per level:

- **Assertions.** Rules a program can check with no opinion: the output is valid JSON, it has the required fields, it avoids words it must never use.
- **A judge.** Quality is not a rule. A *judge* (here a model, or a person) scores each answer from 1 to 5 on a *rubric*, a short list of criteria such as accuracy and tone. A judge can be wrong, so a few answers are also scored by humans, and the two are compared.
- **Regression.** For every test question, how did the new version do against the old one? Better, worse, or the same? Running a question twice can give two different results, so a small change may be luck and not progress.
- **The gate.** Everything above, put into one decision, with the reasons, and with every failure on a question that was not in the golden set turned into a proposal for a new golden case.

Nothing in this problem calls a model. The outputs, and the scores of the judge and of the humans, arrive as data, so every result is exact and the same in every language. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

Aim to finish in 150 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 40, level 2 by 80, level 3 by 110 and level 4 by 140, keeping the last minutes for a final run.

## Input

- `ReleaseGate()`: creates an empty gate.
- A **case id**, a **run name**, a **criterion** and a **field name** are 1 to 20 characters from `a` to `z`, `0` to `9` and `_`. They are compared exactly as given and sorted by the numeric value of their characters, so digits come before `_`, which comes before letters.
- An **input** or an **output** is text of 0 to 300 characters, each a space, a tab, a newline or a visible ASCII character (`!` to `~`). It is what the assistant was asked and what it answered.
- A **score** is a whole number from 1 (worst) to 5 (best). A **pass score** is a whole number from 1 to 5.
- Each level's section describes the methods it adds and their parameters.

## Output

Methods answer with a number, a list of text, a list of rows of text, or nothing, as each section says. Numbers inside rows are written in decimal as text. "Sorted" means compared by the numeric value of the characters of each column in turn.

## Level 1: Assertions on outputs

An **assertion** is a rule that an output must satisfy, whatever its quality. Cheap to run, with no ambiguity, assertions catch the failures that break a program downstream: text where JSON was promised, a missing field, a forbidden word.

- `setSchema(rows)`: sets the shape of a valid output, replacing any earlier one. Each row is `[name, type, requirement]`: a field name, one of the types below, and `required` or `optional`. An empty list means no field is required.
- `setBannedWords(words)`: sets the words that an output may never contain, replacing any earlier list. Each word is lowercase, from `a` to `z` and `0` to `9`.
- `check(output)`: the list of reasons why the output fails, in the order below, or `[]` when it passes.
- `addRun(run, caseIds, inputs, outputs)`: stores a run: the output for each case. `inputs[i]` and `outputs[i]` belong to `caseIds[i]`. A run with the same name that was stored before is replaced as a whole. It returns the number of cases. The input of a case is the same text in every run that holds it.
- `checkRun(run)`: one row `[caseId, "pass" or "fail", reason...]` for each case of the run, sorted by case id, with the reasons of `check` after the verdict. `[]` for a run that does not exist.

**The reasons**, in this order:

1. **JSON.** The output must be a valid JSON text as written in the JSON standard (RFC 8259): one value and nothing else but spaces, tabs and line breaks around it. `NaN`, `Infinity`, single quotes, comments, a trailing comma and a number with a leading zero are not JSON. If it is not, the reason is `json`, and the fields are not looked at.
2. **Object.** The JSON value must be an object (`{...}`). A list, a number, a string, `true` and `null` give `object`, and the fields are not looked at.
3. **Fields.** For each row of the schema, in the order of the schema: if the field is absent, `missing:<name>` when it is required (and nothing when optional); if it is present with the wrong type, `type:<name>`. A field gives at most one reason. Fields that the schema does not name are ignored. When a field appears twice in the text, the last one counts.
4. **Banned words.** The *words* of the output are found in the raw text, in lowercase: a word is a longest run of the characters `a` to `z` and `0` to `9`. Capitals do not matter, and anything else (a quote, a space, an underscore, a backslash) ends a word. For each banned word that is one of the words of the output, `banned:<word>`, once, in sorted order. The text is read as it is written: an escape such as `g` is not decoded.

**The types.** `string` is a JSON string. `int` is a JSON number whose value is a whole number (`3`, `3.0`, `1e2` and `-0` all count, `3.5` does not; `true` is not a number). `bool` is `true` or `false`. `strings` is a list in which every item is a string (and may be empty). `null` is none of them.

### Example 1

<!-- case: ex1 -->

The first output has every required field and the optional list is a list of strings: it passes. The second is a sentence followed by JSON, which is not JSON as a whole. The third is a list, not an object. The fourth has `confidence` as text, which gives `type:confidence`, and no `needs_human`, which gives `missing:needs_human`; the reasons follow the order of the schema. The fifth contains `guaranteed`. The sixth has `Obviously` in another case and a list with a number in it.

### Example 2

<!-- case: ex2 -->

The run is reported by case id, whatever the order it was stored in. `c1` is valid JSON with `answer` but without two required fields. `c3` is plain text. A run that was never stored has no rows.

## Level 2: Judge scores and human labels

Some qualities have no rule. Is the answer correct, polite, short enough? A **judge** scores them on a **rubric**: each answer gets a score from 1 to 5 on each **criterion**. Using a model as a judge is cheap and scales, and it is not neutral: a judge can have biases, such as favouring longer answers or the first answer it reads (see the explanation's further reading). So a few answers, the **calibration subset**, are also scored by humans. A human score is the better evidence: where there is one, it replaces the judge's. And the two are compared, to learn how far to trust the judge.

- `addScores(run, criteria, caseIds, scores)`: stores the judge's scores for cases of a run: `scores[i][j]` is the score of `caseIds[i]` on `criteria[j]`. It replaces the judge's scores of the run (not the humans'), and returns the number of cases.
- `addHumanScores(run, caseIds, criteria, scores)`: the same shape, for the human scores. A human score is for a cell (case, criterion) that the judge has scored. A new human score for a cell replaces the older one. It returns the number of cells set.
- `aggregate(run)`: one row `[criterion, mean, humanCells]` for each criterion, sorted by name, and a last row `["overall", mean, humanCells]`. The **effective score** of a cell is the human score when there is one and the judge's otherwise. `mean` is the mean of the effective scores of the criterion over the scored cases, **in hundredths of a point**, rounded to the nearest, a tie rounded up: `floor((200 * sum + n) / (2 * n))`. `humanCells` is how many of those cells have a human score. The overall row covers every cell. `[]` for a run with no scores.
- `agreement(run, passScore)`: for each criterion that has at least one human score, sorted by name, a row `[criterion, labelled, agreePercent, kappa]`, described below. `[]` for a run that does not exist.
- `disagreements(run, passScore)`: the cells with a human score where the judge and the human are on different sides of the pass score, as rows `[caseId, criterion, judgeScore, humanScore]` sorted by case id and then criterion.

**What the judge and the human said.** A score of at least `passScore` is a **pass** and a lower one a **fail**. Only this verdict is compared, so that a 4 from the judge and a 5 from a human agree when the pass score is 4. Only the judge's own score is used (never the effective one), against the human's.

**Agreement.** For a criterion, take its cells with a human score: `labelled` is their number, and `agreePercent` is the share where the judge and the human gave the same verdict, as a whole percent rounded **down**.

**Cohen's kappa.** Agreement counts the cases where both say pass because both are lenient. *Cohen's kappa* corrects for the agreement that two raters would reach by chance given how often each says pass: `kappa = (po - pe) / (1 - pe)`, where `po` is the observed agreement and `pe` the agreement expected by chance. It is 1 for perfect agreement, 0 for no better than chance and negative for worse than chance. With `a` cells where both say pass, `b` where only the judge does, `c` where only the human does and `d` where both fail, and `N = a + b + c + d`:

```text
chance = (a + b) * (a + c) + (c + d) * (b + d)
kappa  = (N * (a + d) - chance) / (N * N - chance)
```

(This is the formula above multiplied by `N^2` top and bottom, so every number is a whole number.) The column `kappa` is `1000 * kappa` **rounded to the nearest whole number, a tie rounded away from zero**, as text (`"400"`, `"-333"`). When `N * N - chance` is `0` (both raters said the same single verdict every time, so chance explains everything) the kappa is not defined and the column is `"undefined"`.

### Example 1

<!-- case: ex3 -->

The judge's accuracy and tone means are both 3.33 (`333`). The humans score four answers on accuracy: the new mean is 3.67 (`367`) with 4 human cells, and the overall mean over all twelve cells is `350`. At a pass score of 4 they agree on 1 of 4 answers (25%): the judge passed `c2` and the human did not, and for `c3` and `c5` it was the other way round, which `disagreements` lists. The kappa is negative, `-500`: they agree less than chance would.

### Example 2

<!-- case: ex4 -->

Ten answers, scored once by the judge and once by a human. They agree on 7 (70%); the judge passed 6 and the human 5, and the kappa is `400`, so a 70% agreement is a good deal less impressive than it looks. In the second run both always say pass, so chance explains all of it: `"undefined"`. In the third run they disagree every time: `-1000`.

## Level 3: Regression against a baseline

A change can fix some questions and break others while the average hardly moves. So each test question is compared on its own. The **baseline** is the version in production and the **candidate** is the change. Each is a list of runs, because running a question more than once shows how much the result moves by chance alone.

- `compare(baselineRuns, candidateRuns, passScore)`: one row for each case of the **first baseline run**, sorted by case id. Every run holds all of these cases (and a candidate run may hold more, which this method ignores).
- `summarize(baselineRuns, candidateRuns, passScore)`: `[regressions, improvements, same, toFail, toPass]`: the number of rows with each `change`, and the number of rows with each of the flips below.

**The score of a case** in a run is the sum of its effective scores over the criteria of the run.

**The verdict of a case** in a run is *pass* when it has no reason at all: its output passes the assertions of level 1, and every one of its effective scores is at least `passScore`. Otherwise it is *fail*.

**Change, and the noise.** Run it again and the same version can score differently. A rule that treats every difference as real will raise false alarms, so a change counts only when it is larger than the spread of the runs: the case has *regressed* when the **best** candidate score is lower than the **worst** baseline score (`max(candidate) < min(baseline)`), *improved* when the **worst** candidate score is higher than the **best** baseline score (`min(candidate) > max(baseline)`), and is otherwise the **same**: the two ranges touch or overlap, and the difference may be chance. With one run on each side this is the plain comparison of two scores.

**Flip.** A version *passes* a case when its verdict is pass in **more than half** of its runs (`2 * passes > runs`, so one pass in two runs is a fail). A **flip** is `pass->fail` when the baseline passes the case and the candidate does not, `fail->pass` in the other direction and `-` otherwise. A flip is about the verdict and a change is about the score, so a case can flip with the same score (a banned word appeared), and can change with no flip.

The row is `[caseId, change, flip, baselineMin, baselineMax, candidateMin, candidateMax, baselinePasses, candidatePasses]`, with `change` one of `regression`, `improvement` and `same`; the four numbers are the lowest and the highest score of the case in the runs of each side; and the last two are `passes/runs`, such as `2/3`.

### Example 1

<!-- case: ex5 -->

One run on each side, pass score 4. Case `a` lost a point and also fell below the pass score: a regression and a flip. `b` gained one. `c` did not move. `d` kept its scores but the candidate's output is not JSON: no change in score, and a flip to fail. `e` was failing and now is not. The totals are 1 regression, 2 improvements, 2 unchanged, 2 flips to fail and 1 to pass.

### Example 2

<!-- case: ex6 -->

Three runs on each side. Case `a` scored 7 to 9 on the baseline and 7 to 8 on the candidate: the ranges overlap, so the **change** is `same`, and yet the baseline passed it in 2 runs of 3 and the candidate only in 1, so it **flips** to fail. Case `b` scored 8 or 9 before and 6 or 7 now: every candidate run is below every baseline run, a regression. Case `c` is an improvement. With a single run on each side (the last call) `a` is the same again but `b` is still a regression.

## Level 4: The release gate

Now the decision. A change is allowed to ship only when:

1. every assertion passes in every candidate run (all the cases, also the new ones);
2. no **critical** case regressed; and
3. the quality of the candidate has not dropped by more than a threshold.

- `configureGate(critical, maxDrop)`: sets the **critical** cases (those whose failure is not acceptable whatever the average does) and the largest drop in quality that is still acceptable, in hundredths of a point, replacing any earlier setting. Until it is called, no case is critical and `maxDrop` is `0`. Every critical case is in the first baseline run.
- `gate(baselineRuns, candidateRuns, passScore)`: the decision, as rows.

**The rows.** The first row is `["decision", "ship"]` or `["decision", "block"]`: `block` when there is at least one reason. Then the reasons, in this order, and then the proposals.

- `["reason", "assertion", run, caseId, reasons]` for each case of each candidate run that fails an assertion (the reasons of `check` joined with commas, such as `missing:confidence,banned:guaranteed`), for the runs in the order given and the cases of a run sorted by id. Here **every** case of the run counts, and not only those of the golden set.
- `["reason", "critical", caseId, change, flip]` for each critical case, sorted by case id, that regressed: its `change` is `regression` or its `flip` is `pass->fail`, as `compare` gives them.
- `["reason", "quality", baselineQuality, candidateQuality, drop, maxDrop]` when `drop > maxDrop` (a drop equal to `maxDrop` is allowed). The **quality** of a side is the mean of the effective scores over every cell of its runs, every criterion and every case of the **golden set**, in hundredths of a point, rounded as in `aggregate`. `drop = baselineQuality - candidateQuality`, which is negative when the candidate is better.

**The golden set** is the cases of the first baseline run. A case of a candidate run that is not in the golden set is a **new** case: a question that production brought and the golden set did not have. It does not take part in `compare` or in the quality, but it does take part in the assertions.

**Proposals.** A failure on a new case is a failure that no test guards against, and the gate turns each into the proposal of a new golden case. A new case **fails** in a run when it has a reason: an assertion reason, or `low:<criterion>` for each criterion (sorted by name) whose effective score in that run is below `passScore`. For each new case that fails in at least one candidate run, sorted by case id, there is a row `["propose", caseId, input, reasons]`, with the reasons of every run in which it failed, joined with commas, each once, sorted. A proposal does not block by itself: a new case that fails only on the judge's score is proposed and the change can still ship. A case of the golden set that fails is not proposed again: it is already a test.

### Example 1

<!-- case: ex7 -->

Critical cases are `c1` and `c3`; a drop of up to 10 hundredths is allowed. The candidate lost a point on `c2` and gained one on `c4`: the quality is the same, `413` both times (the mean 4.125 rounds up). Every output passes. The two new cases `n1` and `n2` are not part of the quality, and `n1` has an accuracy of 2, below the pass score of 4: it is proposed as a golden case, and the change ships.

### Example 2

<!-- case: ex8 -->

The candidate's `c2` contains `guaranteed`, and the new case `n1` is missing two fields: these are the two assertion reasons, in the order of the cases. `c1`, critical, lost a point: a critical regression (its flip is `-`: it still passes). The quality fell from `433` to `367`, which is 66 more than the 10 allowed. The decision is `block`, and the new case that failed an assertion is also proposed.

## Constraints

- At most 300 calls per test. A run has 1 to 20 cases, and there are at most 6 runs on a side. There are at most 6 criteria in a run, and a case id appears once in a run.
- A schema has at most 8 rows with different names. At most 8 banned words. The `type` of a row is `string`, `int`, `bool` or `strings`, and the requirement is `required` or `optional`.
- In `compare` and `gate`, every run named has scores for all of its cases and for the same criteria, and the baseline runs all hold the same cases. A human score is given only to a cell that the judge has scored.
- A number written in an output has at most 30 digits. Outputs and inputs are ASCII.
- `maxDrop` is an integer from 0 to 500.

## Follow-ups

- The gate checks a verdict by a pass score. What would you change to also require that no *criterion* gets worse by more than some amount, and what does that cost in false alarms?
- With two or three repeats the range rule is cheap and conservative. When would you replace it with a statistical test, such as a bootstrap over the cases, and what do you need that this problem does not have?
- Humans labelled only a few answers. How would you choose which ones, so that the kappa says the most about the judge? How many labels does a kappa of 0.4 need before you trust it?
- A judge is often asked to compare two answers to the same question rather than to score one. What biases does that remove, and what new ones appear (the order of the two answers)?
- The golden set grows by one case for each new failure. What happens to the cost of a run after a year, and how would you retire cases without losing coverage?
- A critical case regresses by one point and everything else improves. Should the gate block? Who decides, and how does the output of this problem help them decide?

## Hints

### Hint 1

Think of a test in a program: it checks something and says pass or fail. An eval is a lot of such tests for an assistant. Start with the simplest, the one that needs no opinion: is the answer valid JSON at all? Every language can try to read JSON and tell you if it failed. Do that first and report `json` when it fails, before anything else.

### Hint 2

Keep the checks as a list of reasons that you add to, in the order of the statement, and return the list. Pass is simply an empty list. The types are where the languages disagree: decide what `true` is in your language's idea of a number, and write one small function per type.

### Hint 3

For the banned words, do not search for the word inside the text, or `guaranteed` would match `unguaranteed`. Cut the lowercase text into words first, and look for the banned words among them.

### Hint 4

The tricky part of level 2 is exactness. Compute every mean and every kappa from whole numbers, and round with a whole-number formula such as `(2 * x + y) // (2 * y)` for the nearest, a tie up. For the kappa, count the four cells `a`, `b`, `c` and `d` once, and use the formula of the statement without dividing until the very end.

### Hint 5

Store a run as a table: the cases with their outputs, and the judge's and the human's scores as separate tables. Write the effective score as a small function (human if there is one, otherwise judge) and use it everywhere. Several rules of later levels differ only in what they do with the same effective scores.

### Hint 6

For the regression, compute for each case its score in each run, then take the minimum and the maximum of each side. Write the verdict of a case in a run as one function that returns the list of reasons (assertions and low scores): a case passes when that list is empty, and the same list gives you the reasons of the proposals.

### Hint 7

For the gate, collect the reasons in three groups in the order of the statement, and let the decision be `block` when the combined list is not empty. The quality is the sum of every effective score over the cells of the golden cases of all runs of a side, rounded with the same formula as `aggregate`. For the proposals, take the cases of the candidate runs that are not in the first baseline run, and for each gather the reasons from every run where it failed.
