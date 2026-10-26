"""`cstudy export` and `cstudy import`: progress.db as JSON and back
(docs/specs/cli.md#cstudy-export).

The rows keep their ids and stored values, so importing an export into an empty database
gives the same `cstudy stats`.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass

from coding_study.application.environment import Environment
from coding_study.domain.errors import UsageError
from coding_study.domain.progress_export import export_text, parse_export

EXPORT_FILE = "progress-export.json"
"""The default backup, at the repository root (PRD Q2: the user may commit it)."""


@dataclass(frozen=True, slots=True)
class Backup:
    text: str
    row_counts: Mapping[str, int]
    """Rows per table."""


def export_progress(environment: Environment) -> Backup:
    snapshot = environment.progress.snapshot()
    return Backup(export_text(snapshot, environment.clock.now()), snapshot.row_counts())


def import_progress(environment: Environment, text: str) -> Mapping[str, int]:
    """Restores an export into an empty progress.db; returns the rows per table.

    Raises UsageError for text that is not an export or a database that holds progress.
    """
    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise UsageError(f"not JSON: {error}") from None
    try:
        snapshot = parse_export(document)
    except ValueError as error:
        raise UsageError(str(error)) from None
    environment.progress.restore(snapshot)
    return snapshot.row_counts()
