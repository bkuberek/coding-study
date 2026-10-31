"""What the web UI's Problem view shows of a problem beyond its `cstudy list` row: what `cstudy
start`, `cstudy solution`, `cstudy hint`, `cstudy bench` and `cstudy test --stress` accept for it
(docs/specs/web-ui.md#browsing)."""

from dataclasses import dataclass

from coding_study.application.environment import Environment
from coding_study.application.practice_catalog import is_item
from coding_study.application.run_bench import bench_issue
from coding_study.application.run_tests import stress_oracle
from coding_study.domain.errors import UsageError
from coding_study.domain.hints import problem_hints
from coding_study.domain.levels import level_progress
from coding_study.domain.problem import Approach, Language, ProblemKind, ProblemMeta
from coding_study.domain.problem_files import PROBLEM_FILE

ORACLE_KINDS = frozenset({ProblemKind.FUNCTION, ProblemKind.DESIGN})
"""The kinds `--stress N` can check against an oracle; concurrent problems stress instead."""


@dataclass(frozen=True, slots=True)
class ProblemDetails:
    languages: tuple[Language, ...]
    """The languages `cstudy start` accepts."""
    approaches: tuple[Approach, ...]
    broken: tuple[str, ...]
    """The ids of a concurrent problem's broken references."""
    last_level: int | None
    """None without levels."""
    hints_total: int
    bench: bool
    """Whether `cstudy bench` applies."""
    oracle: bool
    """Whether `cstudy test --stress N` adds oracle inputs."""


ITEM_DETAILS = ProblemDetails((), (), (), None, 0, bench=False, oracle=False)
"""A non-autograded item: no language, no references, levels, hints, bench or oracle."""


def problem_details(environment: Environment, slug: str) -> ProblemDetails:
    """Raises UnknownProblemError for a slug that names no problem or item."""
    if is_item(environment, slug):
        return ITEM_DETAILS
    meta = environment.problems.load(slug).meta
    concurrency = meta.concurrency
    levels = level_progress(meta, None)
    return ProblemDetails(
        languages=meta.languages,
        approaches=meta.approaches,
        broken=tuple(broken.id for broken in concurrency.broken) if concurrency else (),
        last_level=levels.last if levels else None,
        hints_total=len(problem_hints(environment.files.read_text(slug, PROBLEM_FILE) or "")),
        bench=bench_issue(meta) is None,
        oracle=_takes_oracle_inputs(environment, meta),
    )


def _takes_oracle_inputs(environment: Environment, meta: ProblemMeta) -> bool:
    if meta.kind not in ORACLE_KINDS:
        return False
    try:
        stress_oracle(environment, meta)
    except UsageError:
        return False
    return True
