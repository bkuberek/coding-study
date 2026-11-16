"""A workspace with the AI preview set up, for the browser tests of Settings' AI section
(docs/specs/web-ui.md#settings-view): AI on with a model, a key and one consent, made with the
`cstudy` commands a user would run, against no provider."""

import subprocess
import sys
from pathlib import Path

from tests.helpers import mark_workspace
from tests.serve_process import served_environment

SENTINEL_KEY = "sk-ant-settings-0123456789"
"""Never in a page, a response, a log line or a file the workspace holds."""
MODEL = "anthropic:claude-fast-example"
CONFIG = f'[ai]\nenabled = true\nmodel = "{MODEL}"\n'


def config_path(workspace: Path) -> Path:
    return workspace.parent / "config" / "coding-study" / "config.toml"


def credentials_path(workspace: Path) -> Path:
    return config_path(workspace).with_name("credentials.toml")


def _run(workspace: Path, *arguments: str, stdin: str | None = None) -> None:
    subprocess.run(
        [sys.executable, "-m", "coding_study", *arguments],
        env=served_environment(workspace),
        input=stdin,
        stdin=None if stdin is not None else subprocess.DEVNULL,
        text=True,
        capture_output=True,
        check=True,
    )


def plain_workspace(directory: Path) -> Path:
    """A marked workspace with no config: AI is off."""
    return mark_workspace(directory / "workspace")


def ai_workspace(directory: Path) -> Path:
    """A marked workspace with AI on and `MODEL` set, a key for anthropic and a consent to send to
    it for an AI review."""
    workspace = plain_workspace(directory)
    config = config_path(workspace)
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(CONFIG)
    _run(workspace, "ai", "key", "anthropic", stdin=f"{SENTINEL_KEY}\n")
    _run(workspace, "ai", "consent", MODEL, "--purpose", "review")
    return workspace
