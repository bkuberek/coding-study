"""A real `cstudy serve` with code intelligence on whose language server is the scripted fake
(`tests/fake_language_server.py`), for the browser tests of what the editor draws from a server
(docs/specs/web-ui.md#code-intelligence-in-the-editor): the diagnostics, hover, go to definition
and autocomplete tests each play their own script and read what the page shows."""

import subprocess
import sys
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from coding_study.adapters.preferences_fs import FsPreferencesStore
from coding_study.domain.preferences import Preferences, preferences_document
from tests.language_server_scripts import ScriptedServer, fake_node, install_fake_basedpyright
from tests.serve_page import opened_page
from tests.serve_process import RunningServer, running_server, served_environment
from tests.workspaces import workspace_like

PYTHON = ("two-sum", "python")
ROOT = Path("python") / "practice"
"""The tree's root for a single-file Python attempt; the server's own root is `python/`."""
WAIT_MS = 60_000
SEGMENT = ".statusbar .code-intelligence"
ACTIVE_TAB = "[role=tab][aria-selected=true]"
PANEL = ".panel:not([hidden])"
EDITOR = f"{PANEL} .cm-content"
READY = "python · basedpyright · ready"
CAPABILITIES = {
    "textDocumentSync": 2,
    "hoverProvider": True,
    "definitionProvider": True,
    "completionProvider": {"resolveProvider": True, "triggerCharacters": ["."]},
    "signatureHelpProvider": {"triggerCharacters": ["(", ","]},
}
"""What the fake server says it can do: the page asks for no more than a server declares."""
SERVES = {"reply": "initialize", "result": {"capabilities": CAPABILITIES}}


@dataclass
class Lab:
    workspace: Path
    script: ScriptedServer
    server: RunningServer
    attempts: dict[str, int]

    def uri_of(self, path: str) -> str:
        """The `file:` URI of a file of the single-file Python attempt's tree."""
        return (self.workspace / ROOT / path).resolve().as_uri()


type Steps = Sequence[Mapping[str, object]]


@contextmanager
def intelligence_lab(
    practice_workspace: Path,
    base: Path,
    steps: Steps | Callable[[Path], Steps],
    *,
    files: Mapping[str, str | bytes] | None = None,
    preferences: Preferences | None = None,
    problems: Sequence[tuple[str, str | None]] = (PYTHON,),
) -> Iterator[Lab]:
    """A server over a copy of the practice workspace with the Python practice problem started,
    a basedpyright that is the fake playing `steps` (or what `steps` makes of the workspace's
    path, for a script that names files by URI), `files` written (paths from the workspace,
    which may replace the starter file) and `preferences` stored (code intelligence on, unless
    told otherwise). `problems` are started, each as a slug and a language (None for a project)."""
    workspace = workspace_like(practice_workspace, base / "workspace")
    for slug, language in problems:
        language_option = ["--lang", language] if language is not None else []
        subprocess.run(
            [sys.executable, "-m", "coding_study", "start", slug, *language_option, "--no-open"],
            env=served_environment(workspace),
            cwd=workspace,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=True,
        )
    for name, content in (files or {}).items():
        path = workspace / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode())
    install_fake_basedpyright(workspace)
    FsPreferencesStore(workspace).write(
        preferences_document(preferences or Preferences(code_intelligence=True))
    )
    script = ScriptedServer(base / "server.json")
    script.play(*(steps(workspace.resolve()) if callable(steps) else steps))
    with running_server(workspace, variables={"PATH": fake_node(base / "bin", script)}) as running:
        yield Lab(workspace, script, running, opened_page(running).attempts)


def store(lab: Lab, preferences: Preferences) -> None:
    """Replaces the stored preferences; a page picks them up when it reloads."""
    FsPreferencesStore(lab.workspace).write(preferences_document(preferences))


def open_attempt(page: Any, lab: Lab, slug: str = PYTHON[0], *, with_file: bool = True) -> None:
    """The attempt's view; a single-file attempt has its file in the editor, a project's tree
    waits for a click (`with_file` false)."""
    page.evaluate("id => { location.hash = `#/attempts/${id}` }", lab.attempts[slug])
    page.wait_for_selector(EDITOR if with_file else "button.tree-file")


def wait_for_status(page: Any, text: str) -> str:
    """Waits until the status bar's segment starts with `text`; returns all of it."""
    page.wait_for_function(
        "([selector, text]) => document.querySelector(selector)?.textContent.startsWith(text)",
        arg=[SEGMENT, text],
    )
    return page.eval_on_selector(SEGMENT, "element => element.textContent")


def active_path(page: Any) -> str:
    """The tree path of the tab in front."""
    return page.get_attribute(ACTIVE_TAB, "title")


def document(page: Any) -> list[str]:
    """The lines of the editor in front, as CodeMirror draws them."""
    return page.locator(f"{EDITOR} .cm-line").all_inner_texts()
