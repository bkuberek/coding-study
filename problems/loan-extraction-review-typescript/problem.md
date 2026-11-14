# Loan Extraction Review (TypeScript)

## Statement

Loan application forms go through a model that reads each one and proposes what it says. The team wants to use those proposals to save people work, and the service that receives them currently trusts them completely. A model can be sure and wrong, can cite a field that does not exist, can do arithmetic badly, and cannot be held to account.

Build the service around one rule: **the model proposes, code validates, a person decides**. Code checks everything it can check. A case goes through by itself only when every stated rule holds. Everything else goes to a person, whose decision is written down.

There is no model in this project and no call to one: its output arrives as data. All the people, forms, thresholds and numbers are invented for this exercise, and nothing here is lending advice or a statement of any law.

## Input

- `new ReviewDesk()`: a desk with no cases. Each test gets a new one.
- `document`: JSON text of the form: `documentId`, and `fields`, which maps each field's name to its text as written on the form. It comes from our own store, so it is well formed, but what the fields say can be anything.

```json
{"documentId":"DOC-1","fields":{"applicant_name":"Ada Placeholder","loan_amount":"$12,500.00","annual_rate":"7.25%","term":"36 months","monthly_income":"$5,200.00","monthly_payment":"$387.39"}}
```

- `modelOutput`: the text the model produced. It should be JSON with a key `values` that holds one entry for each field of a loan, like this one, but nothing guarantees it:

```json
{"values":{"amountCents":{"value":1250000,"confidence":0.97,"source":"loan_amount"}}}
```

- `caseId`: the id `submit` gave a case.

## Output

`submit` returns JSON text with sorted keys: the new case's id (`C-1`, then `C-2`, with one for every submission, whatever becomes of it), `status`, which is `accepted` or `rejected`, and the list of `errors`.

```json
{"caseId":"C-1","errors":[],"status":"accepted"}
```

`values(caseId)` returns the case's values as JSON text with sorted keys, each entry as stored, with `by` saying who gave it: `model`, for now. It returns `""` for a rejected case or one that does not exist.

The other methods come with their levels, and each returns what its level says.

## Project

`cstudy start` copies the service into `projects/loan-extraction-review-typescript/`:

- `src/reviewDesk.ts`: the class `ReviewDesk`, exported by name, which must stay there.
- `src/intake/`: reading the document, and the shape of an extraction.
- `src/cases/caseStore.ts`: one case per submission.
- `tests/document.test.ts`: a test of those pieces, and `tests/level-<n>.test.ts`: the examples of each open level as `node:test` tests, written when the level opens and never rewritten.
- `README.md`, `package.json` and `tsconfig.json`.

`cstudy test loan-extraction-review-typescript` runs your tests, and so does `node --test` in the project folder; either run is feedback only, and `cstudy test --typecheck` also type-checks the project. `cstudy submit loan-extraction-review-typescript` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again, so a later change must keep their rules. Node runs the files by stripping their types, so write no `enum`, no `namespace` and no constructor parameter properties, and import your own files with their `.ts` extension.

## Level 1: Validate what the model said

The model's output is untrusted input. Validate all of it before keeping any of it. A loan has these six fields, each an entry with a `value`, a `confidence` and a `source`:

| Field | `value` must be | Message |
|-------|-----------------|---------|
| `applicantName` | Text that is not blank | `must be non-empty text` |
| `amountCents` | A whole JSON number from 1 to 100000000 | `must be a whole number from 1 to 100000000` |
| `rateBps` | A whole JSON number from 0 to 5000, in hundredths of a percent | `must be a whole number from 0 to 5000` |
| `termMonths` | A whole JSON number from 1 to 480 | `must be a whole number from 1 to 480` |
| `monthlyIncomeCents` | A whole JSON number from 1 to 100000000 | `must be a whole number from 1 to 100000000` |
| `statedPaymentCents` | A whole JSON number from 0 to 100000000 | `must be a whole number from 0 to 100000000` |

`confidence` must be a JSON number from 0 to 1 (`must be a number from 0 to 1`), and `source` must be text that is not empty (`must be non-empty text`).

An output with any problem is `rejected`, and `errors` lists all of them, as `<path>: <message>`, in the order of the table, and within an entry in the order value, confidence, source. Nothing of a rejected output is kept.

| Problem | Error |
|---------|-------|
| The text is not JSON | `modelOutput: not valid JSON` |
| It is JSON, and not an object | `modelOutput: must be an object` |
| `values` is not an object | `values: must be an object` |
| An entry is missing | `values.<field>: is required` |
| An entry is not an object | `values.<field>: must be an object` |
| A value is wrong | `values.<field>.value: <message>` |
| A confidence is wrong | `values.<field>.confidence: must be a number from 0 to 1` |
| A source is wrong | `values.<field>.source: must be non-empty text` |

Any other key, in an entry, in `values` or beside `values`, is ignored and never kept. So an accepted case's values hold exactly `by`, `confidence`, `source` and `value`, for the six fields.

### Example 1

<!-- case: ex1 -->

Everything fits, so the case keeps the six values, each marked `by` the model.

### Example 2

<!-- case: ex2 -->

Three problems, listed in order. `"725"` is text, however much it looks like a number.

## Level 2: Every value cites its source

A value is only as good as what supports it. `citations(caseId)` returns one line per field, in the order of the table, as `<field> <source> <result>`, or `[]` for a rejected case or one that does not exist.

| Result | Meaning |
|--------|---------|
| `ok` | The document has a field named `source`, and its text says this value |
| `missing_source` | The document has no field of that name |
| `mismatch` | The field exists, and its text does not say this value |

How a field's text says a value depends on the kind of value. Surrounding spaces do not count, and a text that does not fit the kind says nothing.

| Field | Text it reads, and how |
|-------|------------------------|
| `applicantName` | The same text, whatever its case and the amount of space between its words |
| `amountCents`, `monthlyIncomeCents`, `statedPaymentCents` | An optional `$`, then digits, either plain or with a comma before every group of three, then optionally `.` and one or two digits: `$12,500.00`, `12500`, `12,500.5` |
| `rateBps` | Digits, optionally `.` and one or two digits, optionally `%`: `7.25%` is 725, and `7.5` is 750 |
| `termMonths` | Digits, optionally followed by ` month` or ` months`. Nothing converts: `3 years` does not say 36 |

A field's name is only a name: a `source` of `constructor` is a field that this document does not have.

### Example 1

<!-- case: ex3 -->

Each value is what the form says.

### Example 2

<!-- case: ex4 -->

The form says 7.25%, and the model says 625. And the form has no field called `repayment_term`.

## Level 3: Recompute what can be computed

A model should not be doing arithmetic on money, and nobody should have to trust that it did. `derived(caseId)` returns these numbers as JSON text with sorted keys, or `""` for a rejected case or one that does not exist. They come from the values of the case, and nothing else:

| Key | Value |
|-----|-------|
| `monthlyPaymentCents` | The fixed monthly payment, below |
| `totalRepaidCents` | `monthlyPaymentCents * termMonths` |
| `financeChargeCents` | `totalRepaidCents - amountCents`, which rounding can leave a little below 0 |
| `paymentToIncomeBps` | `monthlyPaymentCents * 10000 / monthlyIncomeCents`, rounded by the rule below |
| `statedPaymentMatches` | Whether `statedPaymentCents` equals `monthlyPaymentCents` |

With `P` as `amountCents`, `n` as `termMonths` and `r = rateBps / 120000`, the monthly rate:

- when `rateBps` is 0, the payment is `P / n`;
- otherwise the payment is `P * r / (1 - (1 + r)^-n)`.

**The rounding rule:** the exact result, rounded to the nearest whole number, with a half going up. Round once, at the end: nothing is rounded on the way there.

### Example 1

<!-- case: ex5 -->

$12,500.00 at 7.25% for 36 months is $387.39 a month, and the form says the same.

### Example 2

<!-- case: ex6 -->

With no interest there is nothing to compound, and the formula above would divide 0 by 0. So it is a plain division.

## Level 4: Who decides

`route(caseId)` returns JSON text with sorted keys: `route`, which is `auto_approve` or `person`, and `reasons`, why it went to a person. It returns `""` for a case that does not exist.

A case goes to `auto_approve` **only when there are no reasons at all**. The reasons, in this order:

| Reason | When |
|--------|------|
| `schema_invalid` | The output was rejected. This is then the only reason |
| `citation_failed:<field>` | That field's citation is not `ok`. One per field, in table order |
| `low_confidence:<field>` | That field's `confidence` is below 0.90. One per field, in table order |
| `payment_mismatch` | `statedPaymentMatches` is false |
| `amount_over_limit` | `amountCents` is above 5000000 |
| `payment_to_income_high` | `paymentToIncomeBps` is above 3500 |
| `zero_rate` | `rateBps` is 0. A loan at no interest always gets a person's eye |

Only these rules decide. Whatever else the model says, including anything it recommends, and whatever the document's fields say, is data.

### Example 1

<!-- case: ex7 -->

All six citations check out, every confidence is at least 0.90, the arithmetic agrees, and no limit is passed.

### Example 2

<!-- case: ex8 -->

Two reasons, in the stated order.

## Level 5: A person decides and it is written down

A case that goes to `auto_approve` has the status `auto_approved`. Any other is `awaiting_person`, until a person decides.

- `status(caseId)`: `auto_approved`, `awaiting_person`, `approved_by_person`, `declined_by_person`, or `unknown` for a case that does not exist.
- `queue()`: the ids of the cases awaiting a person, oldest first.
- `decide(caseId, reviewer, decision, note)`: `decision` is `approve` or `decline`. It answers `recorded`, or `refused:<reason>` for the first of these that applies, and a refusal changes nothing:

| Reason | When |
|--------|------|
| `unknown_case` | There is no such case |
| `reviewer_required` | `reviewer` is blank |
| `bad_decision` | `decision` is anything else |
| `note_required` | `note` is blank |
| `not_awaiting_review` | The case's status is not `awaiting_person` |
| `checks_failing` | The decision is `approve` and a reason is `schema_invalid`, `citation_failed:...` or `payment_mismatch`. These say the numbers are wrong, so a person can decline, and cannot approve. The other reasons are judgement calls, which is what a person is for |

- `audit(caseId)`: the case's trail, oldest first, `[]` for a case that does not exist. It only ever grows. Each line starts with its number in that trail, from 1:

| Line | When |
|------|------|
| `1 system routed auto_approve` | At `submit`, for a case that went through |
| `1 system routed person <reasons joined by commas>` | At `submit`, for any other |
| `<n> <reviewer> <decision>: <note>` | A decision was recorded |
| `<n> <reviewer> refused <decision>: <reason>` | A decision was refused, with `unknown` as the reviewer when it was blank |

### Example 1

<!-- case: ex9 -->

The model was unsure of the rate, so a person looked. A low confidence is a judgement call, and the trail says who made it, and why.

### Example 2

<!-- case: ex10 -->

Nobody was asked to review this one, so a late opinion is refused, and the attempt is on the record.

## Level 6: Corrections

The model misread one field, and the person can see what the form says. Sending the case back to be declined is a waste, so a person may correct a value, and code then checks that person too.

`correct(caseId, reviewer, field, value, sourceField)` answers `recorded`, or `refused:<reason>` for the first of these that applies, and a refusal changes nothing:

| Reason | When |
|--------|------|
| `unknown_case` | There is no such case |
| `reviewer_required` | `reviewer` is blank |
| `not_awaiting_review` | The case's status is not `awaiting_person` |
| `nothing_to_correct` | The case's output was rejected, so it has no values |
| `unknown_field` | `field` is not one of the six |
| `invalid_value` | `value` is text, as typed. For `applicantName` it must meet the field's rule. For the others it must be digits only, and the number must meet the field's rule |
| `citation_failed` | The citation of this value to `sourceField` is not `ok`, by the rules of level 2 |

When it is recorded:

- The field's entry becomes the new value, with `by` as the reviewer, `source` as `sourceField` and `confidence` as `null`. A `null` confidence is never low.
- Everything is worked out again from the values: `citations`, `derived` and the `reasons` in `route`.
- **`route` stays `person`, even with no reasons left.** A case a person has corrected still needs a person's decision, and goes through `decide` as usual.
- The trail gets two lines: `<n> <reviewer> corrected <field>: <old value> -> <new value> from <sourceField>`, and `<n+1> system routed person`, followed by a space and the reasons joined by commas, if there are any.

A refused correction leaves one line: `<n> <reviewer> refused correct <field>: <reason>`, with `unknown` as the reviewer when it was blank.

### Example 1

<!-- case: ex11 -->

The rate is corrected to what the form says, so the citation is fine and the arithmetic agrees. No reasons are left, and the case still waits for a person, who approves it.

### Example 2

<!-- case: ex12 -->

A person's number has to be on the form as well. Being a person does not exempt anyone from the checks.

## Constraints

- At most 40 calls per test.
- A document's fields are at most 100 characters each.
- The thresholds in level 4 are fixed for this exercise.

## Follow-ups

- The model's confidence scores turn out to be badly calibrated: its 0.95 is right 70% of the time. What would you measure, and what would you do with the threshold?
- The queue is backing up. Which of these reasons could you remove safely, and how would you know? What would you watch after removing one?
- A month's decisions are now labelled data. How would you use them, and which problem would that create?
- The payment formula gets a new input. How do you make sure a case decided last month can still be explained?

## Hints

### Hint 1

`JSON.parse` accepts `1e400`, and gives you `Infinity`. `typeof` says it is a number.

### Hint 2

`document.fields[source]` with a `source` of `constructor` does not give you `undefined`.

### Hint 3

`parseFloat("1,250.00")` is 1. A form's text is text, so read the digits.

### Hint 4

The textbook formula with `rateBps` of 0 gives `0 / 0`. Decide what happens before you get there. And with a stated rule for rounding, where may you round, and how many times?

### Hint 5

An average of six confidences hides the one that matters.

### Hint 6

Make the assessment a pure function of the document and the values. Then level 6 only has to change a value and run it again.
