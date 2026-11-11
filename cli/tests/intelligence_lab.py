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
from coding_study.adapters.toml_config import CONFIG_FILE
from coding_study.domain.preferences import Preferences, preferences_document
from tests.language_server_scripts import (
    ScriptedServer,
    fake_go,
    fake_jdk,
    fake_node,
    fake_rust_analyzer,
    install_fake_basedpyright,
    install_fake_gopls,
    install_fake_jdtls,
    install_fake_kotlin_lsp,
)
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
    path: Path
    """The directory of the fake `node`, first on the served PATH."""

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
    jdk: int | None = None,
    go_and_rust: bool = False,
    kotlin_license: bool | None = None,
    warm_up: bool = False,
) -> Iterator[Lab]:
    """A server over a copy of the practice workspace with the Python practice problem started,
    a basedpyright that is the fake playing `steps` (or what `steps` makes of the workspace's
    path, for a script that names files by URI), `files` written (paths from the workspace,
    which may replace the starter file) and `preferences` stored (code intelligence on, unless
    told otherwise). `problems` are started, each as a slug and a language (None for a project).
    With `jdk`, JDT LS is installed too and the server selects a JDK of that release whose `java`
    is the same fake. With `go_and_rust`, gopls is installed too, a `go` on PATH says Go 1.27 is
    selected, and a `rust-analyzer` on PATH is the same fake. With `kotlin_license`, the Kotlin
    LSP is installed too, its launcher the same fake, and its license accepted when it is true.
    Without `warm_up`, the config's default language is TypeScript, whose server no lab installs,
    so `cstudy serve` starts none ahead of time and every server is a session's; with it, Python,
    whose fake it starts as it starts (docs/specs/web-ui.md#warm-up)."""
    workspace = workspace_like(practice_workspace, base / "workspace")
    config = workspace.parent / "config" / CONFIG_FILE
    config.parent.mkdir(parents=True, exist_ok=True)
    default_language = "python" if warm_up else "typescript"
    config.write_text(f'default_lang = "{default_language}"\n', encoding="utf-8")
    script = ScriptedServer(base / "server.json")
    java: dict[str, str] = {}
    if jdk is not None:
        install_fake_jdtls(workspace)
        java["JAVA_HOME"] = fake_jdk(base / f"jdk-{jdk}", script, jdk)
    for slug, language in problems:
        language_option = ["--lang", language] if language is not None else []
        subprocess.run(
            [sys.executable, "-m", "coding_study", "start", slug, *language_option, "--no-open"],
            env={**served_environment(workspace), **java},
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
    script.play(*(steps(workspace.resolve()) if callable(steps) else steps))
    variables = {"PATH": fake_node(base / "bin", script), **java}
    if go_and_rust:
        install_fake_gopls(workspace, script)
        fake_go(base / "bin")
        fake_rust_analyzer(base / "bin", script)
    if kotlin_license is not None:
        install_fake_kotlin_lsp(workspace, script, accepted=kotlin_license)
    with running_server(workspace, variables=variables) as running:
        yield Lab(workspace, script, running, opened_page(running).attempts, base / "bin")


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


POINT_AT = """([line, column]) => {
  const element = document.querySelectorAll('.panel:not([hidden]) .cm-line')[line];
  const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
  let remaining = column;
  for (let node = walker.nextNode(); node !== null; node = walker.nextNode()) {
    if (remaining <= node.length) {
      const range = document.createRange();
      range.setStart(node, remaining);
      range.setEnd(node, Math.min(remaining + 1, node.length));
      const box = range.getBoundingClientRect();
      return { x: box.left + box.width / 2, y: box.top + box.height / 2 };
    }
    remaining -= node.length;
  }
  throw new Error(`no column ${column} on line ${line}`);
}"""


def point_at(page: Any, line: int, column: int) -> dict[str, float]:
    """The middle of the character at a 0-based line and column of the editor in front, in the
    page's coordinates."""
    return page.evaluate(POINT_AT, [line, column])
