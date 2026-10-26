"""The run record: one stress run's expanded scripts joined with the runner's outputs.

Spec: docs/specs/problem-format.md#run-record. Invariants and `stress_checker.py` read only this
record. Values are collected in record order: setup, then workers (group declaration order,
worker index, op order), then final.
"""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass

from coding_study.domain.cases import JsonValue
from coding_study.domain.runs import SectionCounters, StressCompleted
from coding_study.domain.stress import Scope, Selector
from coding_study.domain.stress_runs import PlannedRun, WorkerScript


@dataclass(frozen=True, slots=True)
class RecordedOp:
    op: str
    args: tuple[JsonValue, ...]
    output: JsonValue

    def value(self, selector: Selector) -> JsonValue:
        index = selector.argument_index
        return self.output if index is None else self.args[index]

    def document(self) -> dict[str, JsonValue]:
        return {"op": self.op, "args": list(self.args), "output": self.output}


@dataclass(frozen=True, slots=True)
class RecordedWorker:
    script: WorkerScript
    ops: tuple[RecordedOp, ...]


@dataclass(frozen=True, slots=True)
class StressRecord:
    run: int
    seed: int
    variant: str
    setup: tuple[RecordedOp, ...]
    workers: tuple[RecordedWorker, ...]
    final: tuple[RecordedOp, ...]
    sections: Mapping[str, SectionCounters]

    def values(self, selector: Selector) -> list[JsonValue]:
        """The selected values in record order."""
        return [value for _, sequence in self.sequences(selector) for value in sequence]

    def sequences(self, selector: Selector) -> list[tuple[str, list[JsonValue]]]:
        """For `source_order`: one labelled sequence per worker (`producer[0]`), and setup
        and final as one each."""
        return [
            (label, [entry.value(selector) for entry in entries if entry.op == selector.op])
            for label, entries in self._reached_by(selector)
        ]

    def document(self) -> dict[str, JsonValue]:
        """The record as `stress_checker.py` receives it."""
        return {
            "run": self.run,
            "seed": self.seed,
            "variant": self.variant,
            "setup": [entry.document() for entry in self.setup],
            "workers": [
                {
                    "group": worker.script.group,
                    "index": worker.script.index,
                    "ops": [entry.document() for entry in worker.ops],
                }
                for worker in self.workers
            ],
            "final": [entry.document() for entry in self.final],
            "sections": {
                name: {
                    "entries": counters.entries,
                    "violations": counters.violations,
                    "max_occupancy": counters.max_occupancy,
                }
                for name, counters in self.sections.items()
            },
        }

    def _reached_by(self, selector: Selector) -> Iterator[tuple[str, tuple[RecordedOp, ...]]]:
        whole_run = selector.group is None
        if whole_run and selector.scope in (Scope.SETUP, Scope.ALL):
            yield Scope.SETUP.value, self.setup
        if selector.scope in (Scope.WORKERS, Scope.ALL):
            for worker in self.workers:
                if selector.group in (None, worker.script.group):
                    yield worker.script.label, worker.ops
        if whole_run and selector.scope in (Scope.FINAL, Scope.ALL):
            yield Scope.FINAL.value, self.final


def stress_record(planned: PlannedRun, completed: StressCompleted) -> StressRecord:
    """Joins the runner's outputs, already checked to match the scripts' shape."""
    setup = planned.scenario.setup
    final = planned.request.final
    return StressRecord(
        run=planned.run,
        seed=planned.seed,
        variant=planned.variant.value,
        setup=_recorded(setup.ops, setup.args, completed.setup),
        workers=tuple(
            RecordedWorker(script, _recorded(script.ops, script.args, outputs))
            for script, outputs in zip(planned.workers, completed.workers, strict=True)
        ),
        final=_recorded(final.ops, final.args, completed.final) if final else (),
        sections=completed.sections,
    )


def _recorded(
    ops: tuple[str, ...], args: tuple[tuple[JsonValue, ...], ...], outputs: tuple[JsonValue, ...]
) -> tuple[RecordedOp, ...]:
    return tuple(
        RecordedOp(op, arguments, output)
        for op, arguments, output in zip(ops, args, outputs, strict=True)
    )
