# Learn Go first

## The idea

cstudy problems assume you can already write a small function in the language you practise: take some input, loop over it, decide things with `if`, and return a result. This page is for you if you want to practise in Go and are not there yet. It lists what to learn first and where to learn it for free, from Go's own documentation.

**What to learn before your first problem:**

- Packages, and `func` with typed parameters and results, including more than one result.
- Variables with `var` and `:=`, and the basic types `int`, `int64`, `float64`, `bool`, `string` and `rune`.
- `if`, `switch`, and `for`, which in Go is also the `while` loop, including `for i, v := range nums`.
- Slices such as `[]int`, `len`, `append`, and maps.
- Errors returned as values, and reading a compiler error.

**Where to learn it:**

- [Tutorial: Get started with Go](https://go.dev/doc/tutorial/getting-started): install Go, write "Hello, World!" and run it with `go run`. It assumes some programming experience; the code is simple.
- [A Tour of Go](https://go.dev/tour/), an interactive introduction in your browser, with exercises at the end of each section.
- [Effective Go](https://go.dev/doc/effective_go), once you can write Go: tips for clear, idiomatic code.

All three are linked from [go.dev/learn](https://go.dev/learn/).

You are ready when you can write, without looking anything up, a function that takes a `[]int` and returns how many of its values are even.

## A worked example

When you start a problem, cstudy writes a file for you to fill in, a **stub**. This is the stub that `cstudy start two-sum --lang go` writes in `go/practice/two_sum/two_sum.go`:

```go
// Two Sum.
//
// You get an integer array nums and an integer target. Exactly two
// positions in nums hold values that add up to target. Find those two
// positions and return them.
//
// Statement: .statements/two-sum.md
// Run: cstudy test two-sum

package two_sum

func twoSum(nums []int, target int) []int {
	panic("not implemented")
}
```

Read it line by line:

1. The lines starting with `//` are comments: a short summary of the problem and the two commands you need.
2. `package two_sum` names the package of this folder. Leave it as it is.
3. `func twoSum(nums []int, target int) []int` declares the function cstudy's tests call. In Go the type comes after the name: `nums` is a slice of `int`, `target` is an `int`, and the `[]int` after the parentheses is the result. Keep the name and the signature.
4. `panic("not implemented")` stops the program with that message, a run-time error on purpose, so that the tests fail clearly on the untouched stub. You replace it with your code.

To fill it in you would loop over the indexes of `nums`, compare values and return a new slice of two indexes, such as `[]int{i, j}`. [Your first problem](../your-first-problem/guide.md) walks through starting, testing and finishing this problem.

## Check your toolchain

cstudy needs Go 1.25 or newer for Go problems. Go is optional: without it, every other language still works. Install it as the [toolchains guide](https://github.com/bkuberek/coding-study/blob/main/docs/guides/toolchains.md#go) shows, then run `cstudy doctor` and look for the `go` row.

```console
$ cstudy doctor
WARN  go not found on PATH    fix: needed for --lang go, install Go 1.25 or newer: https://github.com/bkuberek/coding-study/blob/main/docs/guides/toolchains.md#go
```

That is the row before Go is installed: a `WARN`, not a `FAIL`, because Go is optional. Once Go is on your `PATH`, the row reads `ok` with its version; an older Go keeps the `WARN`. The `dlv` row is about Delve, the debugger that only `cstudy test --debug` needs.

## When to use it

- **Read this page** before your first problem in Go, if writing a loop or a function in Go still needs looking up.
- **Skip it** if you can already write a function that loops over a slice and returns a result: go straight to [your first problem](../your-first-problem/guide.md).
- **Choose Go** if you work with Go, or want to write services and command-line tools in it.

## Common traps

- **`append` may return a new slice.** The specification: if the slice's capacity is not large enough, `append` "allocates a new, sufficiently large underlying array". Always assign the result: `out = append(out, x)`.
- **`:=` in an inner block makes a new variable.** The specification: an identifier declared in a block "may be redeclared in an inner block". `total := 0` inside an `if`, when `total` already exists outside it, creates a second `total` that disappears at the end of the block, and the outer one never changes.
- **`range` gives you copies.** In `for i, v := range items`, `v` is the value `items[i]` copied into a variable. Changing `v` does not change the slice; write `items[i] = ...` to change an element.
- **Integer overflow is silent.** The specification: for signed integers, overflow "does not cause a run-time panic"; the result is still defined, just wrong for your purpose. `int` is either 32 or 64 bits, depending on the implementation; use `int64` when you need 64 bits for sure.
- **Unused variables and imports do not compile.** Go's FAQ: "Go refuses to compile programs with unused variables or imports". Remove them, or the build fails before any test runs.
- **Map order changes.** Iterating over a map gives the keys in an order that is not specified, and not guaranteed to be the same from one loop to the next. Sort the keys when the order matters.

## Complexity

cstudy's problems state the time and space their solutions take, in Big-O notation, and many have a large hidden input that a slow solution does not finish in time.

| Operation | What the documentation says | Source |
|-----------|-----------------------------|--------|
| A map lookup, insert or delete | A map is a hash table, which offers "fast lookups, adds, and deletes" | The Go blog, *Go maps in action* |
| `append` with spare capacity | Reuses the underlying array | The specification |
| `append` without spare capacity | Allocates a new, larger array and copies into it | The specification |
| `len(s)` and `cap(s)` | Stored in the slice itself: a slice is a descriptor of an array segment, holding a reference to the array, the length and the capacity | The Go blog, *Go Slices: usage and internals* |

A loop inside a loop over the same slice of n items does about n² steps. That is fine for ten items and too slow for a hundred thousand, the length of the largest input of several easy problems.

## Expert notes

- **The Go cstudy uses.** cstudy builds with your installed Go and `GOTOOLCHAIN=local`, so it never downloads another toolchain; with a Go older than 1.25 it stops with an error instead.
- **Its own build settings.** cstudy pins its build environment (`GOENV=off`, `GOFLAGS=-mod=readonly`, `GOPROXY=off`), so your `go env -w` settings do not change how it builds. They still apply to the `go` commands you run yourself.
- **No downloads.** The runner uses the standard library only, plus one module that ships with cstudy for decimal values, so Go problems need no network.
- **Loop variables since Go 1.22.** Before Go 1.22 the variables a `for` loop declares were created once and updated by each iteration; since 1.22 each iteration creates new ones, "to avoid accidental sharing bugs". Older articles and answers may describe the old behaviour.

## Practice

Start with [your first problem](../your-first-problem/guide.md), which walks through the whole loop on a real problem.

After that, two problems are built on Go traps from this page:

- `debug-shadowed-variable`: a checkout total that compiles, passes `go vet`, and still charges customers the wrong amount. Find out why and fix it.
- `debug-range-value-copy`: a month-end loyalty statement in which points above the cap never expire. Find out why and fix it.

## Further reading

- [go.dev/learn](https://go.dev/learn/): the official learning resources.
- [Tutorial: Get started with Go](https://go.dev/doc/tutorial/getting-started): installing Go and running your first program.
- [A Tour of Go](https://go.dev/tour/): the interactive introduction.
- [Effective Go](https://go.dev/doc/effective_go): idiomatic Go, `panic` and errors.
- [The Go specification](https://go.dev/ref/spec): `append`, scopes and redeclaration, `range`, integer types and overflow, and loop variables.
- [Go 1.22 release notes](https://go.dev/doc/go1.22): a new loop variable for each iteration.
- [Go FAQ](https://go.dev/doc/faq): why unused variables and imports do not compile.
- [Go maps in action](https://go.dev/blog/maps): maps as hash tables, missing keys, and iteration order.
- [Go Slices: usage and internals](https://go.dev/blog/slices-intro): slices, length and capacity.
- [Install the language toolchains: Go](https://github.com/bkuberek/coding-study/blob/main/docs/guides/toolchains.md#go): cstudy's install steps and build settings.
