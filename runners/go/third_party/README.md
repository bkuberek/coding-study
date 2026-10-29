# Vendored Go modules

Go builds run with `GOPROXY=off` and `GOFLAGS=-mod=readonly`, so they never download a module (docs/specs/runners.md#go-build-details). The modules a solution may import are copied here and reached through `replace` directives: in `runners/go/go.mod`, in the workspace's `go/go.mod`, and in the `go.work` of the generated build.

| Module | Version | Source | `go.sum` hash |
|---|---|---|---|
| `github.com/shopspring/decimal` | v1.5.0 (commit `f658fbf1eb94abc869558633a0b9b239300899f4`) | https://proxy.golang.org | `h1:HxSWk31RmJv0EyY4oLiGQB9u7WPludUwPBdvQZnYFPc=` |

Each copy keeps the module's `go.mod`, `LICENSE`, `README.md` and non-test `.go` files; tests, benchmarks, CI files and the changelog are left out. To update a module, download the new version into an empty module cache (`GOMODCACHE=$(mktemp -d) go mod download -json <module>@<version>`), copy the same files over the old ones, and change the version here and in every `require` that names it.
