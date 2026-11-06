"""Whether a run or a job works on a workspace, whichever process started it
(docs/specs/cli.md#cstudy-reset): a runner names its files under `.cs/runs/` on its command line,
and a child of `cstudy serve` starts with `-m coding_study --workspace <root>`.
"""

from collections.abc import Callable
from pathlib import Path

from coding_study.adapters.process_liveness import processes_naming
from coding_study.domain.layout import RUNS_DIRECTORY

_SERVER_CHILD = "-m coding_study --workspace"


class ProcessRunActivity:
    """`RunActivity` over the machine's processes. A `cstudy test` still building, before its runner
    starts, names nothing it can be told by."""

    def __init__(self, root: Path, naming: Callable[..., list[int]] = processes_naming) -> None:
        self._root = root
        self._naming = naming

    def active_run(self) -> str | None:
        texts = (
            text
            for root in {self._root, self._root.resolve()}
            for text in (f"{root / RUNS_DIRECTORY}/", f"{_SERVER_CHILD} {root} ")
        )
        pids = self._naming(*texts)
        return f"a run or a job is in progress (process {pids[0]})" if pids else None
