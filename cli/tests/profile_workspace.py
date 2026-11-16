"""Workspaces with a learner profile, for the browser tests that need one
(docs/specs/cli.md#the-learner-profile): made by `cstudy init --lang`, with the config the profile
reads, and, for a removal the page must refuse to delete, an attempt in progress."""

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from coding_study.adapters.sqlite.progress_store import SqliteProgressStore
from coding_study.domain.attempts import AttemptMode, NewAttempt
from coding_study.domain.config import DEFAULT_PROGRESS_DB
from coding_study.domain.problem import Language
from tests.serve_process import served_environment

LANGUAGES = ("python", "go")
ROLES = ("backend",)
DOMAINS = ("security", "backend")


def profiled_workspace(
    directory: Path,
    languages: tuple[str, ...] = LANGUAGES,
    roles: tuple[str, ...] = ROLES,
    domains: tuple[str, ...] = DOMAINS,
) -> Path:
    """A workspace made by `cstudy init` for `languages`, with a config that narrows the job
    roles and domains, so the profile hides rows in every view that filters."""
    flags = [flag for language in languages for flag in ("--lang", language)]
    workspace = directory / "workspace"
    subprocess.run(
        [sys.executable, "-m", "coding_study", "init", str(workspace), *flags],
        env=served_environment(workspace),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=True,
    )
    config = workspace.parent / "config" / "coding-study" / "config.toml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        f"[profile]\njob_roles = {json.dumps(list(roles))}\ndomains = {json.dumps(list(domains))}\n"
    )
    return workspace


def with_attempt_in_progress(workspace: Path, slug: str, language: Language) -> Path:
    """`workspace` with an attempt of `slug` in `language` in progress, which a removal of that
    language's folder is refused for."""
    store = SqliteProgressStore(workspace / DEFAULT_PROGRESS_DB)
    store.add_attempt(NewAttempt(slug, language, AttemptMode.NEW, datetime.now(UTC)))
    return workspace
