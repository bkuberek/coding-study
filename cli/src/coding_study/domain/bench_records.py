"""What a bench run stores in `bench_runs` and the machine state it ran under.

Spec: docs/specs/progress-and-scheduling.md#schema and performance-analysis.md#environment-record.
The scheduling penalty reads an attempt's latest `verdict` and `confidence` as a `BenchOutcome`.
"""

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from coding_study.domain.bench_stats import TargetSeries
from coding_study.domain.bench_verdict import Confidence, Verdict
from coding_study.domain.cases import JsonValue
from coding_study.domain.problem import Language

BENCH_SEED = 1
SEED_BYTES = 8
MAX_BATCH_CALLS = 100_000
BATCH_INPUT_BUDGETS: Mapping[Language, int] = {
    Language.PYTHON: 10**6,
    Language.TYPESCRIPT: 10**7,
    Language.JAVA: 10**7,
    Language.KOTLIN: 10**7,
}
"""Calls per sample times the input's elements stays under this, bounding the decoded copies held
at once: a Python list element costs about 36 bytes, a JVM or V8 array element 4 to 8."""


def bench_seed(slug: str, size: int) -> int:
    """The generator seed for one ladder size: identical for every target and every run."""
    digest = hashlib.sha256(f"{slug}:{size}:{BENCH_SEED}".encode()).digest()
    return int.from_bytes(digest[:SEED_BYTES], "big")


def max_batch(elements: int, language: Language) -> int:
    budget = BATCH_INPUT_BUDGETS[language]
    return max(1, min(MAX_BATCH_CALLS, budget // max(elements, 1)))


def input_elements(document: JsonValue) -> int:
    """What one decoded copy of a generated input holds: list items and dict values recursively,
    string characters, and 1 per other scalar; at least 1. Counting `n` instead would cap the
    batch of a one-integer input at large n and leave its fast calls too short to time."""
    return max(1, _elements(document))


def _elements(value: JsonValue) -> int:
    if isinstance(value, list):
        return sum(_elements(item) for item in value)
    if isinstance(value, dict):
        return sum(_elements(item) for item in value.values())
    if isinstance(value, str):
        return len(value)
    return 1


class PowerSource(StrEnum):
    AC = "AC"
    BATTERY = "battery"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class MachineState:
    cpu: str
    power: PowerSource
    load_1m: float | None
    cores: int

    @property
    def warnings(self) -> tuple[str, ...]:
        """Conditions that cap every confidence at medium (performance-analysis.md#confidence)."""
        found: list[str] = []
        if self.power is PowerSource.BATTERY:
            found.append("on battery power")
        if self.load_1m is not None and self.load_1m > self.cores / 2:
            found.append(f"load {self.load_1m:.1f} is above half of {self.cores} cores")
        return tuple(found)


@dataclass(frozen=True, slots=True)
class BenchRunRecord:
    attempt_id: int | None
    """None for `--refs-only`."""
    slug: str
    language: Language
    ran_at: datetime
    code_hash: str | None
    sizes: tuple[int, ...]
    series: tuple[TargetSeries, ...]
    """Every target, the user's code included, as `results` stores them."""
    verdict: Verdict
    confidence: Confidence
    user_time_band: str | None = None
    user_memory_band: str | None = None
    slope: float | None = None
    r2: float | None = None
    reference_id: str | None = None
    ratio: float | None = None
    environment: Mapping[str, JsonValue] | None = None
    """cpu, power, load, cores, runtime and references_hash."""


@dataclass(frozen=True, slots=True)
class BenchOutcome:
    """The verdict and confidence a stored bench run ended with."""

    verdict: Verdict
    confidence: Confidence

    @property
    def is_confident_suboptimal(self) -> bool:
        """What `schedule.penalize_suboptimal` acts on: `suboptimal` at medium or high (PRD Q8)."""
        return self.verdict is Verdict.SUBOPTIMAL and self.confidence is not Confidence.LOW
