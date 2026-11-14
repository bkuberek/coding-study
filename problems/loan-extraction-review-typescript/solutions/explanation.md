# Loan Extraction Review (TypeScript): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | O(c) per queue read; O(f) per other call | O(c f + a) | default answer: validate, then a pure assessment of each extraction, with the decision kept for a person |

Here `f` is the number of fields, which is six, `c` the number of cases and `a` the audit lines.

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | Schema | `src/intake/validateModelOutput.ts`, which also decides what gets kept |
| 2 | Citations | `src/checks/normalize.ts`, the readers, and `src/checks/citations.ts` |
| 3 | Arithmetic | `src/money/loanMath.ts`, in `BigInt` |
| 4 | Routing | `src/review/assessment.ts`: one pure function from the document and the values to the citations, the numbers and the reasons |
| 5 | Decisions | `src/review/decisions.ts`, states on the case and an audit trail of text |
| 6 | Corrections | One more function there, which changes a value and runs `assess` again |

## Approach: reference (A pure assessment of each extraction with the decision kept for a person)

### Intuition

What makes a system like this safe isn't how accurate the model is. It is what happens when the model is wrong, which it will be, in ways that look exactly like when it is right. So the design treats its output as a claim from an unreliable witness, and asks what can be checked without trusting it:

- **Its shape.** Does it fit the schema? That is ordinary input validation, and it needs the ordinary care: `"725"` isn't a number, `1e400` isn't a value, and anything the schema does not name does not get in.
- **Its evidence.** Does the document say what the model says it says? A citation is only useful if code follows it. This is the check that catches an invented number, however confident the model is.
- **Its arithmetic.** Anything that can be computed gets computed by code, and the model's figure becomes something to compare against, never something to use.

What's left after that is judgement, and judgement belongs to a person, who has a name and gives a reason. Confidence scores are useful as a way to choose what a person looks at, and they are not evidence.

The other half of the design is what the rules can't do. Auto-approve means "every stated rule held", and it should be a small, boring set that you can read out loud. No score and no recommendation can extend it, and a person who has corrected something has taken the case out of it for good. A log of why every case went where it went is what lets someone argue with those rules later, with data.

### Say it out loud

"The rule is: the model proposes, code validates, a person decides. I treat the model's output as untrusted input and validate it against a schema before anything else touches it, the way I would any request. A schema failure still makes a case, because the document still needs someone.

"Next, provenance. Every value has to cite a field, and I check that the field exists and actually says that. Anything that can be recomputed is recomputed, so a payment comes from a formula, in integer cents, with one stated rounding rule. The model's number is only ever a thing to compare.

"Routing is deterministic: a short list of reasons, and auto-approve only when there are none. Confidence is the minimum across fields, not an average, because one bad field is what hurts. I'd treat the threshold as something to calibrate against real outcomes, because a model's confidence isn't a probability until you've measured that it is.

"And the trail is append-only text: who, what, why, including refused attempts. A person can approve past a limit, because that's a judgement call. They can't approve a number that code has shown is wrong: they correct it, code checks the correction too, and they still have to decide."

### Algorithm

1. `submit`: parse the output and validate it against the table. Keep only the fields the schema names, or keep nothing and list every error.
2. `assess`: follow each citation, recompute the numbers, and list the reasons, in the stated order. It is a pure function of the document and the values.
3. A case with no reasons is `auto_approved`. Any other is `awaiting_person`. Either way, write the route on line 1 of the trail.
4. `decide`: check the stated conditions in order. On a refusal, write the attempt to the trail and change nothing. Otherwise record the state and the note.
5. `correct`: check the stated conditions in order, including the citation of the new value. Then replace the entry, run `assess` again, mark the case as no longer able to go through alone, and write both lines.

### Design

| File | Responsible for |
|------|-----------------|
| `src/reviewDesk.ts` | `ReviewDesk`: the order of the steps, and the JSON |
| `src/intake/document.ts` | Reading the form. Unchanged from the starter |
| `src/intake/extraction.ts` | The six fields and the rule for each value, which both a submission and a correction use |
| `src/intake/validateModelOutput.ts` | Untrusted text to clean values, or a list of errors |
| `src/checks/normalize.ts` | Reading a form's text as a number, on the digits |
| `src/checks/citations.ts` | Whether the document says it, using `Object.hasOwn` so that `constructor` is not a field |
| `src/money/loanMath.ts` | The payment and everything from it, exact, in `BigInt` |
| `src/review/assessment.ts` | Everything code can say about a case, in one pure function, and the thresholds, on one page |
| `src/review/decisions.ts` | What a person may do, and the audit lines |
| `src/cases/caseStore.ts` | The cases, with their state, reasons and trail |
| `tests/loanMath.test.ts` | The arithmetic on hand-worked values, and the readers |

**Why `BigInt`, when floats get the same answer?** Run over about 13 million loans with everyday amounts, rates and terms, the float formula with a final `Math.round` gave the same cent as the exact result every time. The reason for `BigInt` is the rule, not the results: "exact, rounded once, half up" is true by construction, with nothing to argue about in an audit, and a float gives you a value that you then have to defend. What does go wrong with floats is the intermediate rounding that money code tends to attract, such as a monthly rate rounded to six places, which is a cent off on real loans (`h25`).

### Next in production

- Log the model's version, the prompt's version and the document's hash on every case, next to the output. A decision you cannot trace to what produced it cannot be defended or fixed.
- Measure whether confidence means anything: of the values the model calls 0.95, how many does a person correct? Move the threshold on that evidence, per field. A single global number is a starting point.
- Treat every auto-approve as a sample to review. Send a random few percent to a person anyway, so that you have a measure of the error rate on what nobody looks at.
- Turn corrections into an evaluation set, and run new model versions against it before rolling them out, with a limited rollout and a kill switch that sends everything to a person.
- Watch the mix of reasons over time. A jump in `citation_failed` is often a new form layout, seen before anyone complains.
- Make the audit trail append-only in the store too: separate write permissions, no updates, and an export that compliance can read without engineering's help. Have someone qualified read what the rules imply for your market, since these thresholds are invented.
- Defend the document path: a form's text reaches the model as input, so a line that tries to give it instructions is an attack. These checks limit what that attack can achieve, and they don't stop a wrong value that the document does in fact say.

### Correctness

Only `validateModelOutput` puts model data into a case, and it copies the four known keys of the six known fields. So a recommendation, an extra key or a value of the wrong type cannot reach anything downstream, and every later step can rely on its types.

`assess` depends only on the document and the values, so its results cannot go stale: a correction runs it again, and every reading comes from the latest. `autoApprovable` is true only when the first assessment has no reasons, and nothing sets it back to true, so a case goes through by itself only if every rule held and no person touched it.

`decide` and `correct` change a case only after all their checks pass, and each check that refuses writes a line and returns first. So a refusal changes nothing but the trail. The trail is an array of strings made at the moment, and only `writeAudit` adds to it, so an old line can't change as the case does.

`monthlyPaymentCents` works in integers: over a common denominator, the formula is one fraction with no rounding on the way, and `divideHalfUp` applies the stated rule once, exactly. So the result is right for every input in range. Zero is handled before the formula, where it would divide 0 by 0.

### Complexity

- Time: O(c) per queue read; O(f) per other call — six fields, each with a fixed amount of work, since a form's text is bounded. The `BigInt` power is bounded too, by the longest term, 480 months.
- Space: O(c f + a) — six values per case, plus every line of every trail.

### Trade-offs

- **A hard stop on failed checks against an override.** Here a person cannot approve over a failed check, and must correct or decline. That is strict: a form whose stated payment is really wrong can only be declined. A real team might allow an override with a second person's signature, at the price of a path around the rule.
- **Minimum confidence against a model-wide score.** A minimum is pessimistic, and sends more to people, but it can't hide the one bad field. An aggregate looks better on a dashboard, and it fails exactly when it matters.
- **Exact citation against a fuzzy match.** Strict reading refuses `twelve thousand five hundred dollars` even though a person could read it. Being strict costs review time, and being lax costs trust in what `ok` means. Prefer strict, and widen it where the data shows you should.
- **Keeping rejected outputs as cases.** It adds rows to the queue, and it's the only way that a document does not silently disappear.
- **Text lines for the audit against rows.** Text is easy to read and hard to query. A real trail stores structured events, and renders text from them.

### Pitfalls and edge cases

Each wrong approach below was run as a one-line change on the reference, through `cstudy submit`, and each fails the cases named with it.

**Trusting the output.**

- **Keeping the values and reporting the errors.** A rejected output must leave nothing behind. Caught by `ex2`, `h4` and `h7`.
- **Spreading an entry into the store.** Whatever the model added comes along. Caught by `h3`.
- **Stopping at the first error.** Caught by `ex2`, `h4` and `h7`.
- **`Number(value)`.** `"725"` passes as a number. Caught by `ex2` and `h6`.
- **`typeof value === "number"` and a range check.** 1.5 passes, and `Number.isInteger` is what says otherwise. Caught by `h6`.
- **A confidence that is only checked to be a number.** Caught by `ex2` and `h7`.
- **`JSON.parse` with no `try`.** Prose from the model takes down the request. Caught by `h1` and `h9`.
- **`typeof x === "object"`.** An array and `null` are objects too. Caught by `h2` and `h8`.

**Citations.**

- **`fields[source] === undefined`.** `fields["constructor"]` is a function, so a made-up citation looks real. Caught by `h12`.
- **Checking only that the field exists.** The model cites `loan_amount` and invents the number. Caught by `ex4`, `h11` and `h14`.
- **`parseFloat` for money.** `parseFloat("12500 USD")` is 12500, and `parseFloat("12,50,0")` looks fine once the commas are gone. Caught by `h14`.
- **Loose commas in the pattern.** Caught by `h14`.
- **Dropping the cents.** Caught by `ex3` and `h15`.
- **A single digit after the point read as cents.** `12,500.5` then reads as `12,500.05`. Caught by `h15`.
- **`parseFloat` for a rate.** `7.25% APR` reads as 725, and `7.255%` rounds into a real value. Caught by `h16`.
- **`parseInt` for a term.** `3 years` reads as 3, and `36 weeks` as 36. Caught by `h17`.
- **An exact string compare on names, or a prefix.** Too strict for a form, and too loose for a person's name. Caught by `h18`.

**Arithmetic.**

- **No case for a rate of zero.** The formula gives `0 / 0`. Caught by `ex6`, `h19` and `h20`.
- **Rounding down.** Caught by `ex5` and `h20`.
- **Rounding a half to even.** A money rule you did not state. Caught by `h20` and `h21`.
- **Rounding the monthly rate early.** A cent off on real loans. Caught by `ex5` and `h25`.
- **Treating the annual rate as monthly.** Caught by `ex5` and `h22`.
- **Using the model's or the form's payment.** Then there is nothing left to compare. Caught by `h28` and `ex8`.
- **Clamping the finance charge at 0.** It hides what rounding did. Caught by `h19` and `h26`.
- **Rounding the ratio down.** Caught by `ex5` and `h21`.

**Routing.**

- **`<=` on the confidence threshold, or `>=` on a limit.** The stated rule is at the boundary. Caught by `h31`, `h33` and `h34`.
- **Averaging confidence.** One bad field among five good ones goes through. Caught by `h31` and `h32`.
- **Leaving out a rule.** Amount: `h33` and `h46`. Zero rate: `h35`. Stated payment: `ex8`. Citations: `h37`.
- **Letting high confidence excuse a failed citation.** Confidence is a claim, and a citation is evidence. Caught by `h37`.
- **Honouring what the model recommends.** Caught by `h38`.
- **Dropping a rejected output.** Its document then disappears. Caught by `h45` and `h51`.

**People.**

- **Letting a person approve over a failed check.** Caught by `h43`, `h44` and `h45`.
- **Refusing every approval that has a reason.** Then a person can't do what they're there for. Caught by `ex9` and `h46`.
- **A later decision replacing the first.** Caught by `ex10` and `h47`.
- **Not auditing refusals.** The attempt is the evidence. Caught by `ex10`, `h43` and `h47`.
- **A blank note or a blank reviewer.** `" "` is blank. Caught by `h48`.
- **A trail you can rewrite.** Caught by `h45` and `ex11`.
- **Newest first in the queue.** Caught by `h51`.

**Corrections.**

- **Trusting a person's value.** People misread forms too. Caught by `ex12` and `h59`.
- **Not running the checks again.** The numbers and the reasons go stale. Caught by `ex11`, `h55` and `h56`.
- **Letting a corrected case go through by itself.** Caught by `ex11`, `h54` and `h57`.
- **Keeping the model's confidence on a person's value.** The old doubt never clears. Caught by `h54` and `h55`.
- **Marking a person's value as the model's.** Caught by `h54` and `h58`.
- **`Number(value)` on the typed text, or no range check.** `1e3` is a number, and so is `5001`. Caught by `h59`.
- **Correcting a case already decided.** Caught by `h60`.
- **`field in {...}`.** `constructor` passes. Caught by `h59`.
- Project traps: `src/reviewDesk.ts` must export `ReviewDesk` by name; local imports need their `.ts` extension; `enum`, `namespace` and constructor parameter properties make Node refuse the file before any test runs.
