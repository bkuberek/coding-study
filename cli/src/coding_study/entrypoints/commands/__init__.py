"""One module per `cstudy` command; entrypoints/cli.py registers them all, in this order."""

from collections.abc import Callable

import typer

from coding_study.entrypoints.commands import (
    bench,
    doctor,
    done,
    export,
    hint,
    history,
    ide,
    import_progress,
    init,
    list_problems,
    mock,
    new,
    next_problem,
    serve,
    show,
    solution,
    start,
    stats,
    status,
    submit,
    test,
    verify,
)

COMMAND_REGISTRATIONS: tuple[Callable[[typer.Typer], None], ...] = (
    init.register,
    doctor.register,
    ide.register,
    start.register,
    test.register,
    submit.register,
    status.register,
    history.register,
    serve.register,
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
