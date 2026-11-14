# Bank Project

A small Go module that grows over four levels. Each level adds methods to `Bank` and builds on the code you wrote for the levels before it, so how you split the code into files and packages is up to you and part of the exercise.

## Contract

- `bank.go` declares the type `Bank` and its constructor `NewBank` in package `bank`, at the root of the module `bank-project-go`. Keep them there: `cstudy submit` imports that package by the module path `go.mod` names.
- `NewBank()` takes no arguments and returns a `*Bank`.
- Each level names the methods it adds, with their parameter and result types. Keep those method names and types; the methods are exported, and their parameter names are yours.

Everything else is yours: grow or replace `account.go`, add files to package `bank`, add packages of your own under this folder, and add your own tests next to the code or under `tests/`.

## Layout

| Path | Holds |
|------|-------|
| `bank.go` | `Bank` and `NewBank`, with level 1's methods to implement |
| `account.go` | `account`, a first model type |
| `tests/level_<n>_test.go` | The examples of each open level, in package `tests_test`, written by `cstudy` when the level opens; yours to edit, never rewritten |
| `go.mod` | The module `bank-project-go` |
| `go.work` | Written by `cstudy start`; it keeps the workspace's own `go.work` out of this folder |

## Running the tests

From this folder:

```sh
go test ./...
go test ./tests -run 'TestEx1$'
go vet ./...
```

From the workspace, `cstudy test bank-project-go` runs the same tests.

The files under `tests/` form one package, which sees only what package `bank` exports. When a level opens, its file calls methods you have not written yet, so that package does not compile until they exist; `cstudy test bank-project-go --level <n>` leaves out the files of the levels above `<n>`. A test file of your own in package `bank`, next to the code, can reach unexported names too.

`go.mod` reaches the vendored `github.com/shopspring/decimal` through its `replace` line, so nothing is downloaded and there is no `go.sum`. Keep it free of other requirements.

## Grading

Your tests are feedback only. `cstudy submit bank-project-go` grades every case of the open levels, hidden ones included, against `Bank`, and opens the next level when they all pass. Editing a test file never changes a grade.
