# Bank Project

A small TypeScript project that grows over four levels. Each level adds methods to `Bank` and builds on the code you wrote for the levels before it, so how you split the code into modules is up to you and part of the exercise.

## Contract

- `src/bank.ts` exports the class `Bank` by name. Keep the file and the export where they are: `cstudy submit` imports `Bank` from `src/bank.ts`.
- `new Bank()` takes no arguments.
- Each level names the methods it adds, with their parameters and return types. Keep those names and signatures.

Everything else is yours: grow or replace `src/models.ts`, add modules under `src/`, and add your own tests under `tests/`.

## Layout

| Path | Holds |
|------|-------|
| `src/bank.ts` | `Bank`, with level 1's methods to implement |
| `src/models.ts` | `Account`, a first model type |
| `tests/level-<n>.test.ts` | The examples of each open level, written by `cstudy` when the level opens; yours to edit, never rewritten |
| `package.json` | An ES module package (`"type": "module"`) with no dependencies, and the `test` and `typecheck` scripts |
| `tsconfig.json` | Strict compiler settings; the types of `node:test` and `node:assert` come from the workspace's `typescript/node_modules` |

Nothing is installed here: the project uses the workspace's Node and TypeScript.

## Running the tests

From this folder:

```sh
node --test
node --test tests/level-1.test.ts
```

`node --test` finds every `*.test.ts` file. From the workspace, `cstudy test bank-project-typescript` runs the same tests.

Node runs TypeScript by stripping the types, without checking them. To type-check, run the workspace's compiler from this folder, or add `--typecheck` to `cstudy test`:

```sh
../../typescript/node_modules/.bin/tsc
```

Because the types are stripped, not compiled, use erasable syntax only: no `enum`, no `namespace` and no constructor parameter properties (`constructor(private id: string)`); Node refuses them with `ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX`. Import your own files with their extension: `import { Account } from "./models.ts";`.

## Grading

Your tests are feedback only. `cstudy submit bank-project-typescript` grades every case of the open levels, hidden ones included, against `Bank`, and opens the next level when they all pass. Editing a test file never changes a grade.
