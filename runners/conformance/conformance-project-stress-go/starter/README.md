# Tally

A Go project on the virtual clock with a stress case for the runner conformance suite: `tally.go` declares the entry type `Tally`, which keeps its counts in `counts.go`.

`cstudy` grades `Tally`, built with `NewTally`: each sequential case in a `testing/synctest` bubble of its own, each stress run on the real clock. Run the tests with `go test ./...`.
