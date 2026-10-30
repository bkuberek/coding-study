"""Building and running one problem's code in one language (docs/specs/runners.md).

Job ids: `<slug>` for the user's code, `<slug>/<approach>` for references.
"""

from collections.abc import Iterable, Sequence
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass

from coding_study.application.environment import Environment
from coding_study.application.ports import (
    BuildFailed,
    BuildScope,
    ProgressNotice,
    References,
    ReferenceSource,
)
from coding_study.domain import layout
from coding_study.domain.concurrency import BrokenReference
from coding_study.domain.judging import RunnableCase
from coding_study.domain.naming import symbol_names
from coding_study.domain.precedence import resolve_hang_guard_ms
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.problem_files import broken_file, solution_file
from coding_study.domain.runs import RunCase, RunJob, RunReport, RunRequest, RunTarget
from coding_study.domain.stress_runs import PlannedRun


@dataclass(frozen=True, slots=True)
class CodeRun:
    build_seconds: float
    report: RunReport | None = None
    """None when the build failed."""
    build_failure: BuildFailed | None = None
    build_note: str | None = None


def reference_job_id(slug: str, approach_id: str) -> str:
    return f"{slug}/{approach_id}"


class LanguageRun:
    def __init__(self, environment: Environment, meta: ProblemMeta, language: Language) -> None:
        self._environment = environment
        self._meta = meta
        self._language = language

    @property
    def language(self) -> Language:
        return self._language

    def user_job(self, cases: Sequence[RunnableCase], stress: Sequence[PlannedRun] = ()) -> RunJob:
        """Concurrent problems also run `stress`, after the sequential cases."""
        target = layout.user_target(self._meta, self._language, str(self._environment.root))
        return self._job(self._meta.slug, target, cases, stress)

    def reference_job(
        self,
        approach_id: str,
        cases: Sequence[RunnableCase],
        stress: Sequence[PlannedRun] = (),
    ) -> RunJob:
        target = layout.reference_target(
            self._meta, approach_id, self._language, str(self._environment.root)
        )
        return self._job(reference_job_id(self._meta.slug, approach_id), target, cases, stress)

    def references(self, approach_ids: Iterable[str]) -> References:
        """The reference files of these approaches in this language."""
        files = self._environment.files
        sources = (
            ReferenceSource(
                approach_id,
                files.path(
                    self._meta.slug,
                    solution_file(layout.reference_file_name(approach_id, self._language)),
                ),
            )
            for approach_id in approach_ids
        )
        return References(self._meta, tuple(sources))

    def broken_references(self, brokens: Iterable[BrokenReference]) -> tuple[ReferenceSource, ...]:
        """Broken reference files, materialized under their `broken-<id>` approach ids."""
        files = self._environment.files
        return tuple(
            ReferenceSource(
                broken.approach_id,
                files.path(
                    self._meta.slug,
                    broken_file(layout.reference_file_name(broken.id, self._language)),
                ),
            )
            for broken in brokens
        )

    def run(
        self,
        scope: BuildScope,
        jobs: Sequence[RunJob],
        notify: ProgressNotice,
        runner_slot: AbstractContextManager[object] | None = None,
    ) -> CodeRun:
        """Build what `scope` needs, then run `jobs` in one runner process, holding
        `runner_slot` (when given) while the runner runs but not while it builds."""
        clock = self._environment.clock
        started = clock.monotonic()
        prepared = self._environment.toolchains.runner(self._language).prepare(scope, notify)
        build_seconds = clock.monotonic() - started
        if isinstance(prepared, BuildFailed):
            return CodeRun(build_seconds, build_failure=prepared)
        with runner_slot or nullcontext():
            report = self._environment.runner_process.run(prepared.launch, RunRequest(tuple(jobs)))
        return CodeRun(build_seconds, report, build_note=prepared.build_note)

    def _job(
        self,
        job_id: str,
        target: RunTarget,
        cases: Sequence[RunnableCase],
        stress: Sequence[PlannedRun],
    ) -> RunJob:
        concurrency = self._meta.concurrency
        return RunJob(
            job_id=job_id,
            kind=self._meta.kind,
            target=target,
            names=symbol_names(self._meta.signature, self._language),
            signature=self._meta.signature,
            cases=(
                *(self._run_case(case) for case in cases),
                *(run.run_case() for run in stress),
            ),
            model=concurrency.model_for(self._language) if concurrency else None,
        )

    def _run_case(self, case: RunnableCase) -> RunCase:
        hang_guard_ms = resolve_hang_guard_ms(
            self._environment.config, case.hang_guard_ms, self._meta.hang_guard_ms
        )
        return RunCase(case.id, case.input, hang_guard_ms)
