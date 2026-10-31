"""`python -m coding_study`: the `cstudy` console script, so a child that `cstudy serve` starts with
`sys.executable -m coding_study` is always the same install as the server
(docs/specs/web-ui.md#process)."""

from coding_study.entrypoints.launcher import main

if __name__ == "__main__":
    main()
