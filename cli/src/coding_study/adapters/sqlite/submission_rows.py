"""Rows of `submissions` and `level_unlocks` (docs/specs/progress-and-scheduling.md#schema)."""

import json
import sqlite3
from datetime import UTC, datetime

from coding_study.domain.judging import Tally
from coding_study.domain.submissions import LevelTally, LevelUnlock, SubmissionRecord

_SUBMISSION_INSERT = """
INSERT INTO submissions (attempt_id, submitted_at, code_hash, graded_up_to, every_level, levels,
  total, passed, failed, errored, timed_out, duration_ms)
VALUES (:attempt_id, :submitted_at, :code_hash, :graded_up_to, :every_level, :levels, :total,
  :passed, :failed, :errored, :timed_out, :duration_ms)
"""


def insert_submission(connection: sqlite3.Connection, submission: SubmissionRecord) -> None:
    tally = submission.tally
    connection.execute(
        _SUBMISSION_INSERT,
        {
            "attempt_id": submission.attempt_id,
            "submitted_at": _instant_text(submission.submitted_at),
            "code_hash": submission.code_hash,
            "graded_up_to": submission.graded_up_to,
            "every_level": int(submission.every_level),
            "levels": json.dumps([_level_json(level) for level in submission.levels]),
            "total": tally.total,
            "passed": tally.passed,
            "failed": tally.failed,
            "errored": tally.errored,
            "timed_out": tally.timed_out,
            "duration_ms": submission.duration_ms,
        },
    )


def submissions(connection: sqlite3.Connection, attempt_id: int) -> tuple[SubmissionRecord, ...]:
    rows = connection.execute(
        "SELECT * FROM submissions WHERE attempt_id = ? ORDER BY submitted_at, id", (attempt_id,)
    ).fetchall()
    return tuple(_submission(row) for row in rows)


def insert_level_unlock(connection: sqlite3.Connection, unlock: LevelUnlock) -> None:
    """A level opens once: a second row for it is ignored."""
    connection.execute(
        "INSERT OR IGNORE INTO level_unlocks (attempt_id, level, unlocked_at) VALUES (?, ?, ?)",
        (unlock.attempt_id, unlock.level, _instant_text(unlock.unlocked_at)),
    )


def level_unlocks(connection: sqlite3.Connection, attempt_id: int) -> tuple[LevelUnlock, ...]:
    rows = connection.execute(
        "SELECT * FROM level_unlocks WHERE attempt_id = ? ORDER BY level", (attempt_id,)
    ).fetchall()
    return tuple(
        LevelUnlock(row["attempt_id"], row["level"], datetime.fromisoformat(row["unlocked_at"]))
        for row in rows
    )


def _level_json(level: LevelTally) -> dict[str, int]:
    return {
        "level": level.level,
        "total": level.total,
        "passed": level.passed,
        "visible_total": level.visible_total,
        "visible_passed": level.visible_passed,
        "hidden_total": level.hidden_total,
        "hidden_passed": level.hidden_passed,
    }


def _level(fields: dict[str, int]) -> LevelTally:
    return LevelTally(
        level=fields["level"],
        visible_total=fields["visible_total"],
        visible_passed=fields["visible_passed"],
        hidden_total=fields["hidden_total"],
        hidden_passed=fields["hidden_passed"],
    )


def _submission(row: sqlite3.Row) -> SubmissionRecord:
    levels: list[dict[str, int]] = json.loads(row["levels"])
    return SubmissionRecord(
        attempt_id=row["attempt_id"],
        submitted_at=datetime.fromisoformat(row["submitted_at"]),
        code_hash=row["code_hash"],
        graded_up_to=row["graded_up_to"],
        every_level=bool(row["every_level"]),
        levels=tuple(_level(level) for level in levels),
        tally=Tally(
            total=row["total"],
            passed=row["passed"],
            failed=row["failed"],
            errored=row["errored"],
            timed_out=row["timed_out"],
        ),
        duration_ms=row["duration_ms"],
    )


def _instant_text(instant: datetime) -> str:
    return instant.astimezone(UTC).isoformat()
