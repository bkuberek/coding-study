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

From the workspace, `cstudy test {{slug}}` runs the same tests. `go.mod` says `go 1.25`, the release that has `testing/synctest.Test`, and reaches the vendored `github.com/shopspring/decimal` through its `replace` line, so nothing is downloaded; keep it free of other requirements. `cstudy start` writes `go.work` here, which keeps the workspace's own `go.work` out of this folder.

## Testing on the virtual clock

`cstudy` grades and tests this project on a virtual clock. Inside a `testing/synctest` bubble the `time` package reads a clock that moves only while every goroutine waits, so a wait of any length takes no real time. The generated tests in `tests/` run each case with `synctest.Test`; write yours the same way:

```go
synctest.Test(t, func(t *testing.T) {
	a := app.New{{class_name}}()
	go func() { a.Put("a", "x") }()
	synctest.Wait()                 // every other goroutine is blocked
	time.Sleep(time.Second)         // the clock moves one second forward
	synctest.Wait()
})
```

Use only the clock the `time` package reads: a goroutine that waits on a channel, a timer or `time.Sleep` lets time move, and one that waits on a mutex that its holder keeps, spins in a loop or reads real I/O does not, so the case hangs. Stop what you start before a test ends: goroutines still waiting when it ends, or all waiting while no timer is due, are a deadlock. `go test` panics with `deadlock: all goroutines in bubble are blocked`, and `cstudy submit` reports the case as `STALLED` with the operation and the virtual time.

Events due at the same instant happen in no fixed order, so the expected values never depend on it.

## Grading

Your tests are feedback only. `cstudy submit {{slug}}` grades every case of the open levels, hidden ones included, and opens the next level when they all pass.
