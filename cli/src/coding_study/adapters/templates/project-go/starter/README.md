# {{title}}

TODO: one paragraph on what this project builds over its levels.

## Contract

- `app.go` declares the type `{{class_name}}` and its constructor `New{{class_name}}` in the module's root package. Keep them in that package: `cstudy submit` imports it as module `{{slug}}`, which `go.mod` names.
- `New{{class_name}}()` takes no arguments and returns a `*{{class_name}}`.
- Each level names the methods it adds, with their parameters and result types. Keep those names and signatures; the methods are exported.

Everything else is yours: add files and packages, and your own tests next to the code or under `tests/`.

## Running the tests

From this folder:

```sh
go test ./...
```

From the workspace, `cstudy test {{slug}}` runs the same tests. `go.mod` reaches the vendored `github.com/shopspring/decimal` through its `replace` line, so nothing is downloaded; keep it free of other requirements. `cstudy start` writes `go.work` here, which keeps the workspace's own `go.work` out of this folder.

## Grading

Your tests are feedback only. `cstudy submit {{slug}}` grades every case of the open levels, hidden ones included, and opens the next level when they all pass.
