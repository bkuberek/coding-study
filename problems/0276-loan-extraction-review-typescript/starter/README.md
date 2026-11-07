# Loan Extraction Review

Scanned loan forms go through a model that reads them and proposes values. This service takes those proposals, and at the moment it takes them on trust, which is the thing to fix.

There is no model in this project. The model's output arrives as data, as it would from another service, so that every test sees the same answer.

## Contract

- `src/reviewDesk.ts` exports the class `ReviewDesk` by name, and `new ReviewDesk()` takes no arguments. Keep the file and the export where they are: `cstudy submit` imports the class from there.
- Each level names the methods it adds, with their parameters and return types. Keep those names and signatures.

Everything else is yours to change, move or add to.

## Layout

| Path | Holds |
|------|-------|
| `src/reviewDesk.ts` | `ReviewDesk`: what the outside world calls |
| `src/intake/document.ts` | `parseDocument`: the form's fields, as text |
| `src/intake/extraction.ts` | The six fields of a loan, and the shape of one extracted value |
| `src/cases/caseStore.ts` | `CaseStore`: one case per submission |
| `src/json.ts` | `canonicalJson`: JSON with object keys in sorted order |
| `tests/document.test.ts` | A test of how a document is read |
| `tests/level-<n>.test.ts` | The examples of each open level, written by `cstudy` when the level opens; yours to edit, never rewritten |

The rest of the design is yours. A pipeline of small steps, each with a plain input and output, tends to serve well here.

## Running the tests

From this folder:

```sh
node --test
node --test tests/level-1.test.ts
```

From the workspace, `cstudy test loan-extraction-review-typescript` runs the same tests. Node strips the types without checking them; `../../typescript/node_modules/.bin/tsc` here, or `cstudy test --typecheck`, type-checks the project.

Use erasable syntax only (no `enum`, no `namespace`, no constructor parameter properties), and import your own files with their `.ts` extension. Nothing is installed here: the project uses the workspace's Node and TypeScript.

## Grading

Your tests are feedback only. `cstudy submit loan-extraction-review-typescript` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again.

A failure report cuts long values at 200 characters, which can hide the part that differs. `cstudy submit loan-extraction-review-typescript --json` prints them whole.
