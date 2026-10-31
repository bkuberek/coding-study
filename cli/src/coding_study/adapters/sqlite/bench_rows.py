"""`bench_runs` rows (docs/specs/progress-and-scheduling.md#schema): records in, history, the
latest outcome and an attempt's runs out."""

import json
import sqlite3
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from coding_study.domain.bench_records import BenchOutcome, BenchRunRecord, BenchRunSummary
from coding_study.domain.bench_runs import USER_TARGET_ID
from coding_study.domain.bench_stats import SizeStats, TargetSeries
from coding_study.domain.bench_verdict import Confidence, PastRun, Verdict
from coding_study.domain.cases import JsonValue
from coding_study.domain.problem import Language

INSERT = """
INSERT INTO bench_runs (attempt_id, slug, lang, ran_at, code_hash, sizes, results, user_time_band,
  user_mem_band, slope, r2, reference_id, ratio, verdict, confidence, env)
VALUES (:attempt_id, :slug, :lang, :ran_at, :code_hash, :sizes, :results, :user_time_band,
  :user_mem_band, :slope, :r2, :reference_id, :ratio, :verdict, :confidence, :env)
"""
HISTORY = """
SELECT ran_at, results FROM bench_runs
WHERE slug = ? AND lang = ? AND attempt_id IS NOT NULL
ORDER BY ran_at, id
"""
LATEST_OUTCOME = """
SELECT verdict, confidence FROM bench_runs
WHERE attempt_id = ?
ORDER BY ran_at DESC, id DESC
LIMIT 1
"""
ATTEMPT_RUNS = """
SELECT ran_at, verdict, confidence, ratio, reference_id FROM bench_runs
WHERE attempt_id = ?
ORDER BY ran_at, id
"""


def insert_bench_run(connection: sqlite3.Connection, run: BenchRunRecord) -> None:
    connection.execute(
        INSERT,
        {
            "attempt_id": run.attempt_id,
            "slug": run.slug,
            "lang": run.language,
            "ran_at": run.ran_at.astimezone(UTC).isoformat(),
            "code_hash": run.code_hash,
            "sizes": json.dumps(list(run.sizes)),
            "results": json.dumps({series.target_id: _sizes(series) for series in run.series}),
            "user_time_band": run.user_time_band,
            "user_mem_band": run.user_memory_band,
            "slope": run.slope,
            "r2": run.r2,
            "reference_id": run.reference_id,
            "ratio": run.ratio,
            "verdict": run.verdict,
            "confidence": run.confidence,
            "env": json.dumps(dict(run.environment or {})),
        },
    )


def bench_history(
    connection: sqlite3.Connection, slug: str, language: Language
) -> tuple[PastRun, ...]:
    rows = connection.execute(HISTORY, (slug, language)).fetchall()
    return tuple(_past_run(row["ran_at"], json.loads(row["results"])) for row in rows)


def latest_outcome(connection: sqlite3.Connection, attempt_id: int) -> BenchOutcome | None:
    row = connection.execute(LATEST_OUTCOME, (attempt_id,)).fetchone()
    if row is None:
        return None
    return BenchOutcome(Verdict(row["verdict"]), Confidence(row["confidence"]))


def attempt_bench_runs(
    connection: sqlite3.Connection, attempt_id: int
) -> tuple[BenchRunSummary, ...]:
    rows = connection.execute(ATTEMPT_RUNS, (attempt_id,)).fetchall()
    return tuple(
        BenchRunSummary(
            datetime.fromisoformat(row["ran_at"]),
            Verdict(row["verdict"]),
            Confidence(row["confidence"]),
            row["ratio"],
            row["reference_id"],
        )
        for row in rows
    )


def _sizes(series: TargetSeries) -> dict[str, JsonValue]:
    return {str(stats.size): _stats(stats) for stats in series.sizes}


def _stats(stats: SizeStats) -> dict[str, JsonValue]:
    fields: dict[str, JsonValue] = {
        "median_ns": stats.median_ns,
        "spread": stats.spread,
        "cpu_ns": stats.cpu_ns,
        "calls": stats.calls,
        "mem_bytes": stats.memory_bytes,
        "mem_metric": stats.memory_metric,
        "status": stats.status.value,
        "exceeded_ns": stats.exceeded_ns,
    }
    return {key: value for key, value in fields.items() if value is not None}


def _past_run(ran_at: str, results: Mapping[str, Any]) -> PastRun:
    user: Mapping[str, Mapping[str, Any]] = results.get(USER_TARGET_ID, {})
    medians = {
        int(size): float(stats["median_ns"]) for size, stats in user.items() if "median_ns" in stats
    }
    return PastRun(datetime.fromisoformat(ran_at), medians)
