"""One module per `cstudy` command; entrypoints/cli.py registers them all, in this order."""

from collections.abc import Callable

import typer

from coding_study.entrypoints.commands import (
    bench,
    doctor,
    done,
    export,
    hint,
    import_progress,
    init,
    list_problems,
    mock,
    new,
    next_problem,
    show,
    solution,
    start,
    stats,
    test,
    verify,
)

COMMAND_REGISTRATIONS: tuple[Callable[[typer.Typer], None], ...] = (
    init.register,
    doctor.register,
    start.register,
    test.register,
    list_problems.register,
    show.register,
    solution.register,
    done.register,
    verify.register,
    next_problem.register,
    hint.register,
    new.register,
    bench.register,
    stats.register,
    export.register,
    import_progress.register,
    mock.register,
)
