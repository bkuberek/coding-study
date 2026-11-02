# Tally

A Kotlin project on the virtual clock with a stress case for the runner conformance suite: `src/main/kotlin/tally/Tally.kt` defines the entry class `tally.Tally`, whose methods are `suspend` functions that keep their counts in `tally.Counts`.

`cstudy` loads `tally.Tally`. Its sequential cases run on the virtual clock; its stress case runs on worker threads, each of which calls the `suspend` functions and waits for them on the real clock.
