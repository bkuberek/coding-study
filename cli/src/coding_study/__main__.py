"""`python -m coding_study`: the `cstudy` console script, so a child that `cstudy serve` starts with
`sys.executable -m coding_study` is always the same install as the server
(docs/specs/web-ui.md#process)."""

from coding_study.entrypoints.launcher import main

if __name__ == "__main__":
    try:
        main()
    finally:
        # CPython 3.12 and 3.13 exit by SIGINT under `-m` once a KeyboardInterrupt has passed
        # through an `exec()`, as dataclasses use while modules import, even when it was caught.
        # An `exec()` that ends normally clears that, so a cancelled child exits 130.
        exec("", {})
