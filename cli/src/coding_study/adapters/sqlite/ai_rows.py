"""`ai_reviews`, `ai_calls` and `ai_consents` of progress.db
(docs/specs/progress-and-scheduling.md#schema, docs/specs/ai.md#records-and-progress)."""

import json
import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path
from typing import cast

from coding_study.adapters.sqlite.progress_connection import ProgressConnection
from coding_study.domain.ai import AiTask, Provider, Tier
from coding_study.domain.ai_models import ProviderErrorKind
from coding_study.domain.ai_records import (
    CallOutcome,
    Consent,
    ModelCall,
    ReviewItem,
    ReviewRecord,
    Verdict,
)

_CALL_INSERT = """
INSERT INTO ai_calls (purpose, provider, model, tier, attempt_id, local_day, started_at, ended_at,
  outcome, error, input_tokens, output_tokens, counted_tokens, cost_usd)
VALUES (:purpose, :provider, :model, :tier, :attempt_id, :local_day, :started_at, :ended_at,
  :outcome, :error, :input_tokens, :output_tokens, :counted_tokens, :cost_usd)
"""
_REVIEW_INSERT = """
INSERT INTO ai_reviews (attempt_id, format, created_at, provider, model, prompt_version,
  rubric_sha256, notes_sha256, items, summary, quotes_dropped, input_tokens, output_tokens,
  cost_usd, dismissed_at)
VALUES (:attempt_id, :format, :created_at, :provider, :model, :prompt_version, :rubric_sha256,
  :notes_sha256, :items, :summary, :quotes_dropped, :input_tokens, :output_tokens, :cost_usd,
  :dismissed_at)
"""
_NEWEST_FIRST = "ORDER BY review.created_at DESC, review.id DESC"


class SqliteAiStore:
    """`AiStore`; one short-lived connection per call, which migrates the database first, as
    `SqliteProgressStore` does."""

    def __init__(self, path: Path, workspace: Path | None = None) -> None:
        self._connection = ProgressConnection(path, workspace)

    def consent(self, provider: Provider, model: str, purpose: AiTask) -> Consent | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM ai_consents WHERE provider = ? AND model = ? AND purpose = ?",
                (provider, model, purpose),
            ).fetchone()
        return _consent(row) if row is not None else None

    def consents(self) -> tuple[Consent, ...]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM ai_consents ORDER BY provider, model, purpose"
            ).fetchall()
        return tuple(_consent(row) for row in rows)

    def grant_consent(self, consent: Consent) -> None:
        with self._connection() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO ai_consents (provider, model, purpose, granted_at) "
                "VALUES (?, ?, ?, ?)",
                (consent.provider, consent.model, consent.purpose, _instant(consent.granted_at)),
            )

    def revoke_consent(self, provider: Provider, model: str, purpose: AiTask) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM ai_consents WHERE provider = ? AND model = ? AND purpose = ?",
                (provider, model, purpose),
            )
        return cursor.rowcount > 0

    def record_call(self, call: ModelCall) -> None:
        with self._connection() as connection:
            connection.execute(
                _CALL_INSERT,
                {
                    "purpose": call.purpose,
                    "provider": call.provider,
                    "model": call.model,
                    "tier": call.tier,
                    "attempt_id": call.attempt_id,
                    "local_day": call.local_day.isoformat(),
                    "started_at": _instant(call.started_at),
                    "ended_at": _instant(call.ended_at),
                    "outcome": call.outcome,
                    "error": call.error,
                    "input_tokens": call.input_tokens,
                    "output_tokens": call.output_tokens,
                    "counted_tokens": call.counted_tokens,
                    "cost_usd": call.cost_usd,
                },
            )

    def calls_between(self, first: date, last: date) -> tuple[ModelCall, ...]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM ai_calls WHERE local_day BETWEEN ? AND ? ORDER BY started_at, id",
                (first.isoformat(), last.isoformat()),
            ).fetchall()
        return tuple(_call(row) for row in rows)

    def add_review(self, record: ReviewRecord) -> int:
        with self._connection() as connection:
            cursor = connection.execute(
                _REVIEW_INSERT,
                {
                    "attempt_id": record.attempt_id,
                    "format": record.format,
                    "created_at": _instant(record.created_at),
                    "provider": record.provider,
                    "model": record.model,
                    "prompt_version": record.prompt_version,
                    "rubric_sha256": record.rubric_sha256,
                    "notes_sha256": record.notes_sha256,
                    "items": json.dumps([_item_json(item) for item in record.items]),
                    "summary": record.summary,
                    "quotes_dropped": record.quotes_dropped,
                    "input_tokens": record.input_tokens,
                    "output_tokens": record.output_tokens,
                    "cost_usd": record.cost_usd,
                    "dismissed_at": _optional_instant(record.dismissed_at),
                },
            )
        assert cursor.lastrowid is not None
        return cursor.lastrowid

    def review(self, review_id: int) -> ReviewRecord | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM ai_reviews WHERE id = ?", (review_id,)
            ).fetchone()
        return _review(row) if row is not None else None

    def reviews_of_problem(self, slug: str) -> tuple[ReviewRecord, ...]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT review.* FROM ai_reviews AS review "
                "JOIN attempts ON attempts.id = review.attempt_id "
                f"WHERE attempts.slug = ? {_NEWEST_FIRST}",
                (slug,),
            ).fetchall()
        return tuple(_review(row) for row in rows)

    def reviews_of_attempt(self, attempt_id: int) -> tuple[ReviewRecord, ...]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT review.* FROM ai_reviews AS review WHERE review.attempt_id = ? "
                f"{_NEWEST_FIRST}",
                (attempt_id,),
            ).fetchall()
        return tuple(_review(row) for row in rows)

    def dismiss_review(self, review_id: int, at: datetime) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                "UPDATE ai_reviews SET dismissed_at = ? WHERE id = ? AND dismissed_at IS NULL",
                (_instant(at), review_id),
            )
        return cursor.rowcount > 0


def _instant(instant: datetime) -> str:
    return instant.astimezone(UTC).isoformat()


def _optional_instant(instant: datetime | None) -> str | None:
    return _instant(instant) if instant is not None else None


def _consent(row: sqlite3.Row) -> Consent:
    return Consent(
        Provider(row["provider"]),
        row["model"],
        AiTask(row["purpose"]),
        datetime.fromisoformat(row["granted_at"]),
    )


def _call(row: sqlite3.Row) -> ModelCall:
    return ModelCall(
        purpose=AiTask(row["purpose"]),
        provider=Provider(row["provider"]),
        model=row["model"],
        tier=Tier(row["tier"]) if row["tier"] is not None else None,
        attempt_id=row["attempt_id"],
        local_day=date.fromisoformat(row["local_day"]),
        started_at=datetime.fromisoformat(row["started_at"]),
        ended_at=datetime.fromisoformat(row["ended_at"]),
        outcome=CallOutcome(row["outcome"]),
        error=ProviderErrorKind(row["error"]) if row["error"] is not None else None,
        input_tokens=row["input_tokens"],
        output_tokens=row["output_tokens"],
        counted_tokens=row["counted_tokens"],
        cost_usd=row["cost_usd"],
    )


def _item_json(item: ReviewItem) -> dict[str, object]:
    return {
        "number": item.number,
        "area": item.area,
        "criterion": item.criterion,
        "verdict": item.verdict,
        "evidence": list(item.evidence),
        "gaps": item.gaps,
    }


def _item(fields: dict[str, object]) -> ReviewItem:
    evidence = cast(list[object], fields["evidence"])
    return ReviewItem(
        number=int(str(fields["number"])),
        area=str(fields["area"]),
        criterion=str(fields["criterion"]),
        verdict=Verdict(str(fields["verdict"])),
        evidence=tuple(str(quote) for quote in evidence),
        gaps=str(fields["gaps"]),
    )


def _review(row: sqlite3.Row) -> ReviewRecord:
    dismissed_at = row["dismissed_at"]
    return ReviewRecord(
        id=row["id"],
        attempt_id=row["attempt_id"],
        format=row["format"],
        created_at=datetime.fromisoformat(row["created_at"]),
        provider=Provider(row["provider"]),
        model=row["model"],
        prompt_version=row["prompt_version"],
        rubric_sha256=row["rubric_sha256"],
        notes_sha256=row["notes_sha256"],
        items=tuple(_item(fields) for fields in json.loads(row["items"])),
        summary=row["summary"],
        quotes_dropped=row["quotes_dropped"],
        input_tokens=row["input_tokens"],
        output_tokens=row["output_tokens"],
        cost_usd=row["cost_usd"],
        dismissed_at=datetime.fromisoformat(dismissed_at) if dismissed_at is not None else None,
    )
