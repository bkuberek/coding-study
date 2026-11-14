# Eval Release Gate: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| run-tables | optimal | O(R C (K + L)) per call | O(R C (K + L)) | default answer; every level reads the same tables through the same few functions |

Here `R` is the number of runs a call names, `C` the number of cases in a run, `K` the number of criteria and `L` the length of an output.

## How the design grows level by level

| Level | Change | What the gate adds |
|-------|--------|--------------------|
| 1 | Assertions | A parse, a walk over the schema, and a word scan, ending in a list of reasons |
| 2 | The judge and the humans | Two score tables per run, one function for the effective score, and exact integer formulas for the mean and the kappa |
| 3 | Regression | A score per case and run, a range on each side, and a majority of passing runs |
| 4 | The gate | The same comparison, a quality figure over the golden cases, and the reasons collected into one decision |

The choice that pays off is to make **one function** that answers "what are the reasons this case fails in this run?", and to let everything else ask it. Level 1 returns its assertion part. Level 3 calls a case a pass when the list is empty. Level 4 reuses the same list for the proposals. There is also one function for the effective score (human, otherwise judge): a rule that changes only at one place cannot disagree with itself between `aggregate`, `compare` and `gate`.

## Approach: run-tables (One table per run of outputs and scores, and one verdict function for every level)

### Intuition

An eval is a set of tables: for each run, what the assistant answered for each case, and what the judge and the humans scored. Every question the gate answers is a small fold over those tables. The only places that need care are the ones where a number is rounded or a rule has an edge: the half-up mean, the kappa and its undefined case, the noise rule, the majority rule, and the difference between a change of score and a flip of verdict.

### Algorithm

1. Keep the schema and the banned words, a map from run name to its table (cases with their input and output, the criteria, the judge's scores and the humans' scores), the critical cases and `maxDrop`.
2. `check`: parse strictly. Not JSON gives `json`; not an object gives `object`. Otherwise walk the schema rows in order and add `missing` or `type`. Then cut the lowercase text into words (`[a-z0-9]+`) and add `banned:<word>` for each banned word found, sorted.
3. `addRun`, `checkRun`: store the table; report the cases sorted by id with the reasons.
4. `effective(case, criterion)`: the human score if there is one, else the judge's. `aggregate`: for each criterion, the sum and the count of effective scores, `floor((200 * sum + n) / (2 * n))`; then the overall row.
5. `agreement`: for each criterion with human cells, build the pairs (judge passes, human passes); count `a`, `b`, `c`, `d`; compute the percent rounded down and the kappa from the whole-number formula, rounded half away from zero, or `undefined` when the denominator is 0.
6. `compare`: for each case of the first baseline run, the score in each run (sum of effective scores), the min and the max of each side, the change by range separation, and the flip by a strict majority of passing runs. `summarize` counts the rows.
7. `gate`: assertion reasons for every case of every candidate run; the critical reasons from `compare`; the quality of each side over the golden cases, in hundredths; the quality reason when the drop is larger than `maxDrop`; the decision; and a proposal for each new case with a reason in some candidate run.

### Correctness

The reasons are computed in the order of the statement, and every step depends only on the output and the configuration, so `check` is a function of its inputs. The word scan reads the raw text, so it does what the statement says about escapes, and splitting into words before comparing is what makes `unguaranteed` different from `guaranteed`.

The mean in hundredths is `round(100 * sum / n)` with ties up. For whole `sum` and `n`, `floor(x + 1/2) = floor((2x + 1) / 2)`, and with `x = 100 * sum / n` this is `floor((200 * sum + n) / (2 * n))`, which is an integer division: no decimal is involved. The kappa is `(po - pe) / (1 - pe)`; with `po = (a + d) / N` and `pe = chance / N^2`, multiplying top and bottom by `N^2` gives `(N * (a + d) - chance) / (N^2 - chance)`. The denominator is never negative, since `chance` is at most `N^2` (each term of the sum pairs two shares of the same `N`), and it is 0 exactly when `pe = 1`, which is the case where the formula divides by zero. Rounding to the nearest thousandth, a tie away from zero, is `sign * floor((2000 * |num| + den) / (2 * den))`.

The change rule compares ranges: `max(candidate) < min(baseline)` says that every candidate run is worse than every baseline run, so no pairing of runs and no ordering of the repeats could call the case better or equal. With one run a side it is the plain comparison. The flip rule asks for a strict majority, so a tie in the number of passing runs is a fail on both sides, and a case never flips because of a tie.

The gate collects its reasons from three independent conditions, in a fixed order, and the decision is a function of whether any exists. The quality uses the golden cases only, so a candidate run cannot move it by adding easy or hard new cases. A proposal is made for a new case with at least one reason in some candidate run, once, with every reason found, so it does not depend on the order of the runs.

### Complexity

- Time: O(R C (K + L)) per call — each call visits the cases of the runs it names, reads K scores for each and scans each output once (the parse and the word scan are linear in the length L). Sorting the cases of a run adds a logarithmic factor that the bound on the sizes makes negligible.
- Space: O(R C (K + L)) — the tables hold the input, the output and the scores of every case of every run.

### Trade-offs

- Assertions are cheap, deterministic and catch what breaks a program, but say nothing about quality. A judge says something about quality and is noisy and biased. Humans are the reference and are expensive and slow. The levels use each where it is strong: the rules gate, the judge measures, the humans calibrate the judge.
- Cohen's kappa corrects the agreement for chance, which raw agreement does not: two raters who both say pass 90% of the time agree 82% of the time by luck alone. Its weakness is that it depends on how often each category occurs: with 90 cells where both say pass, 5 and 5 where they differ and none where both fail, the raters agree on 90% of the cells and the kappa is -0.053. That is why the percent is reported beside it. With a handful of labels it is also very uncertain, which the problem does not try to measure.
- The range rule for noise is simple, exact and conservative: it never calls a change that the spread of the repeats could explain, and it misses small real changes unless there are enough runs. A statistical test would use all the runs and give a measure of doubt; it needs more runs and assumptions that a gate that must be explainable often avoids.
- The pass score and the majority rule turn scores into a verdict. That is easy to explain and it hides the margin: a case that goes from 5 to 4 and one that goes from 4 to 3 look different only through the pass score. The score columns of `compare` keep the margin visible.
- Blocking on a critical case regardless of the average is a policy and not a statistic. It protects the cases that must not break and it makes the gate stricter than the average would be; the reasons make it a decision a person can overrule knowingly.
- Proposing the failure as a new golden case makes the golden set grow from experience. The cost is the growing price of every run, and the risk that the set drifts towards past failures; deciding what to retire is a human task this problem leaves out.

### Pitfalls and edge cases

- Level 1: JSON is stricter than many parsers' defaults (`NaN`, trailing commas, single quotes, comments and leading zeros are not JSON), and a parser that accepts them gives the wrong reason. A value that is valid but not an object is `object`, not `json`. A field gives at most one reason, `missing` for absent and `type` for present. `true` is not an `int`, although in some languages a boolean is a number. `3.0` and `1e2` are whole numbers, and the test is on the 64-bit double the number reads as: `1e400` overflows to infinity and is not an `int`, while `1.00000000000000000001` rounds to `1` and is. `null` is of no type. A required field that is `null` is `type`, not `missing`. The words are found in the raw text: `no_guaranteed_way` contains `guaranteed` because an underscore ends a word, `unguaranteed` does not, and a key can hold a banned word. A banned word hidden behind an escape is not decoded. An empty schema accepts every object. `checkRun` sorts by the characters, so `case_10` comes before `case_2`.
- Level 2: the nearest hundredth rounds a tie up (`312.5` becomes `313`), which is not what a language's `round` does when it rounds to even. A human score replaces the judge's in the mean but not in the agreement, which compares the two. A new `addScores` keeps the human scores. A criterion without human scores has no agreement row, and the list is sorted by name, while the columns of `addScores` follow the order the caller gave. The percent rounds down (2 of 3 is 66). Kappa is `undefined` when both raters give one verdict throughout, `0` when only one does, and a tie in its rounding goes away from zero (`-312.5` becomes `-313`). The pass score changes everything: the same scores have a different kappa at 3 and at 4.
- Level 3: the golden cases are those of the first baseline run, and extra cases in a candidate run are ignored by `compare`. A change is a strict inequality between ranges, so touching ranges are the same. A flip is a majority rule: one pass in two runs is a fail. A case can flip without a change (the score is the same and an assertion fails), and can change without a flip. A human score counts in the score and in the verdict.
- Level 4: a drop equal to `maxDrop` is allowed, a negative drop never blocks, and the quality is over the golden cases of every run of a side, with the effective scores. The critical reason comes from either the change or the flip. A critical case that was failing already and got worse is a regression. A non-critical regression alone does not block. Assertions block for new cases too, and a new case that fails only on a score is proposed without blocking. A golden case that fails is not proposed. Without a call to `configureGate`, nothing is critical and no drop is allowed.

### Language notes

- Python: `json.loads` accepts `NaN`, `Infinity` and `-Infinity` by default, which the JSON standard does not allow, so pass a `parse_constant` that raises. `bool` is a subclass of `int`, so test for `bool` before `int`. A float such as `3.0` needs `float.is_integer()`. `//` rounds down, which is what the formulas need, also for a negative number. When a name appears twice in an object, the last value wins by default.
- TypeScript: `JSON.parse` is strict and also lets the last of two equal names win. A JSON number is a `number`, so `Number.isInteger` covers `3`, `3.0` and `1e2`, and a `boolean` is not a `number` as it is in Python. Look up a field with `Object.prototype.hasOwnProperty.call`, since `name in object` also finds inherited names such as `constructor`. `%` is negative for a negative left side, so the floor division adds the denominator back. The default `sort()` orders strings by code unit, which is the order of the statement for these names. The numbers stay far below `2^53`, so the arithmetic is exact.

## Further reading

- T. Bray (ed.), RFC 8259, "The JavaScript Object Notation (JSON) Data Interchange Format", IETF, December 2017: the grammar behind the checks of level 1, including that numeric values which cannot be written in the grammar, such as `Infinity` and `NaN`, are not permitted.
- [Python `json`](https://docs.python.org/3.12/library/json.html): documents that the module accepts `NaN` and the infinities although the RFC does not permit them, and that for a repeated name in an object only the last pair is kept.
- [ECMAScript `JSON.parse`](https://tc39.es/ecma262/multipage/structured-data.html): the specification the TypeScript runtime follows; for duplicate names in an object, lexically preceding values for the same key are overwritten.
- J. Cohen, "A Coefficient of Agreement for Nominal Scales", Educational and Psychological Measurement 20(1):37-46, 1960, doi:10.1177/001316446002000104: the origin of kappa.
- [Cohen's kappa](https://en.wikipedia.org/wiki/Cohen%27s_kappa): states the definition `kappa = (p_o - p_e) / (1 - p_e)` used in level 2, with `p_o` the observed agreement and `p_e` the agreement expected by chance.
- L. Zheng et al., "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena", arXiv:2306.05685, 2023: the use of language models as judges, their position, verbosity and self-enhancement biases, and their agreement with human preferences.
- M. T. Ribeiro, T. Wu, C. Guestrin and S. Singh, "Beyond Accuracy: Behavioral Testing of NLP Models with CheckList", Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics, pp. 4902-4912, 2020, doi:10.18653/v1/2020.acl-main.442: a task-agnostic methodology for testing a model's behaviour, inspired by behavioural testing in software engineering, in the spirit of the assertions and golden cases here.
- B. Efron, "Bootstrap Methods: Another Look at the Jackknife", The Annals of Statistics 7(1):1-26, 1979, doi:10.1214/aos/1176344552: the resampling method that the noise follow-up suggests in place of the range rule.
