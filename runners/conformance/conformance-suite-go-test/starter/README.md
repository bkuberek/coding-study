# Probe

A Go project for the runner conformance suite: `probe.go` declares the entry type `Probe`, and the reference adds `tests/statuses_test.go`, whose tests cover every status of a suite job, and `broken/broken_test.go`, which does not compile.

`cstudy` grades `Probe`, built with `NewProbe`, from the root package. Run the tests with `go test ./...`.
