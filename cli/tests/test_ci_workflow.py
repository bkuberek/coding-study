"""The browser job of the CI workflow (docs/specs/versioning.md#what-the-workflow-does): it runs
the Playwright tests of the web UI on Chromium, only when something that can affect the page
changed, it is light, nothing waits for it, and it is not allowed to fail."""

import ast
import fnmatch
import os
import re
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.helpers import REPOSITORY_ROOT

WORKFLOWS = REPOSITORY_ROOT / ".github" / "workflows"
TESTS = REPOSITORY_ROOT / "cli" / "tests"
BROWSER_TESTS = "tests/entrypoints/web/test_browser_*.py"
MAXIMUM_TIMEOUT_MINUTES = 15
NO_COMMIT = "0" * 40
Job = dict[str, Any]
needs_git_and_bash = pytest.mark.skipif(
    shutil.which("git") is None or shutil.which("bash") is None, reason="git and bash are needed"
)


def _load(name: str) -> dict[Any, Any]:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def _triggers(workflow: dict[Any, Any]) -> dict[str, Any]:
    """YAML 1.1 reads the key `on` as the boolean True."""
    return workflow.get("on") or workflow[True]


@pytest.fixture(scope="module")
def jobs() -> dict[str, Job]:
    return _load("ci.yml")["jobs"]


@pytest.fixture(scope="module")
def browser(jobs: dict[str, Job]) -> Job:
    assert "browser" in jobs, f"ci.yml has only the jobs {sorted(jobs)}"
    return jobs["browser"]


@pytest.fixture(scope="module")
def changes(jobs: dict[str, Job]) -> Job:
    assert "changes" in jobs, f"ci.yml has only the jobs {sorted(jobs)}"
    return jobs["changes"]


def _commands(job: Job) -> list[str]:
    return [step["run"] for step in job["steps"] if "run" in step]


def _diff_step(changes: Job) -> Job:
    return next(step for step in changes["steps"] if step.get("id") == "diff")


def test_the_browser_job_runs_on_linux(browser: Job):
    assert browser["runs-on"] == "ubuntu-latest"


def test_the_browser_job_is_light_enough_for_a_free_account(browser: Job):
    assert browser["timeout-minutes"] <= MAXIMUM_TIMEOUT_MINUTES


def test_the_browser_job_is_one_job_without_a_matrix(browser: Job):
    assert "strategy" not in browser


def test_the_browser_job_may_not_fail_without_failing_the_run(browser: Job):
    allowed_to_fail = [browser, *browser["steps"]]
    assert not any(part.get("continue-on-error") for part in allowed_to_fail)


def test_the_browser_job_runs_every_browser_test_file(browser: Job):
    assert any(BROWSER_TESTS in command for command in _commands(browser))


def test_the_browser_job_runs_on_chromium_only(browser: Job):
    runs = [command for command in _commands(browser) if BROWSER_TESTS in command]
    assert all("-k chromium" in command for command in runs)


def test_the_browser_job_installs_chromium_only(browser: Job):
    installs = [command for command in _commands(browser) if "playwright install" in command]
    assert [command.split()[-1] for command in installs] == ["chromium"]


def test_the_browser_job_caches_the_playwright_browsers_and_the_pnpm_store(browser: Job):
    caches = [
        step["with"]["path"]
        for step in browser["steps"]
        if "actions/cache@" in step.get("uses", "")
    ]
    assert sorted(caches) == ["~/.cache/ms-playwright", "~/.local/share/pnpm/store"]


def test_the_browser_job_reports_why_a_test_was_skipped(browser: Job):
    assert any(" -rs " in command for command in _commands(browser))


def test_the_browser_job_runs_only_when_the_web_ui_changed(browser: Job):
    assert (browser["needs"], browser["if"]) == ("changes", "needs.changes.outputs.web == 'true'")


def test_no_other_job_waits_for_anything(jobs: dict[str, Job]):
    waiting = [name for name, job in jobs.items() if name != "browser" and "needs" in job]
    assert waiting == []


def test_ci_runs_on_pushes_and_pull_requests_only():
    assert sorted(_triggers(_load("ci.yml"))) == ["pull_request", "push"]


def test_the_release_workflow_does_not_wait_for_ci():
    assert "workflow_run" not in _triggers(_load("version.yml"))


def _paths(changes: Job) -> list[str]:
    return _diff_step(changes)["env"]["WEB_PATHS"].split()


def _covers(patterns: list[str], path: str) -> bool:
    return any(
        path == pattern or path.startswith(f"{pattern}/") or fnmatch.fnmatchcase(path, pattern)
        for pattern in patterns
    )


def _imported_helpers(module: Path) -> Iterator[Path]:
    """The modules of `tests` that `module` imports, and the scripts it names next to itself."""
    source = module.read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        names = [node.module] if isinstance(node, ast.ImportFrom) and node.module else []
        names += [alias.name for alias in node.names] if isinstance(node, ast.Import) else []
        for name in names:
            helper = REPOSITORY_ROOT / "cli" / Path(*name.split(".")).with_suffix(".py")
            if name.startswith("tests.") and helper.is_file():
                yield helper
    for name in re.findall(r'with_name\("([^"]+\.py)"\)', source):
        yield module.with_name(name)


def _browser_test_closure() -> set[Path]:
    pending = sorted((TESTS / "entrypoints" / "web").glob("test_browser_*.py"))
    found = {TESTS / "conftest.py", TESTS / "entrypoints" / "web" / "conftest.py", *pending}
    while pending:
        for helper in _imported_helpers(pending.pop()):
            if helper not in found:
                found.add(helper)
                pending.append(helper)
    return found


def test_a_change_to_a_module_the_browser_tests_use_runs_the_job(changes: Job):
    paths = _paths(changes)
    uncovered = [
        str(module.relative_to(REPOSITORY_ROOT))
        for module in sorted(_browser_test_closure())
        if not _covers(paths, str(module.relative_to(REPOSITORY_ROOT)))
    ]
    assert uncovered == []


@pytest.mark.parametrize(
    "path",
    [
        "tools/web-ui/src/main.ts",
        "cli/src/coding_study/entrypoints/web/app.py",
        "cli/tests/entrypoints/web/test_browser_smoke.py",
        ".github/workflows/ci.yml",
    ],
)
def test_the_files_of_the_page_run_the_job(changes: Job, path: str):
    assert _covers(_paths(changes), path)


@pytest.mark.parametrize(
    "path",
    [
        "problems/0001-two-sum/problem.md",
        "docs/specs/web-ui.md",
        "cli/src/coding_study/domain/runs.py",
        "cli/tests/entrypoints/web/test_runs_api.py",
        ".github/workflows/version.yml",
    ],
)
def test_the_files_apart_from_the_page_do_not_run_the_job(changes: Job, path: str):
    assert not _covers(_paths(changes), path)


def _git(directory: Path, *arguments: str) -> str:
    identity = (
        "-c",
        "user.name=ci",
        "-c",
        "user.email=ci@example.test",
        "-c",
        "commit.gpgsign=false",
    )
    completed = subprocess.run(
        ["git", *identity, *arguments], cwd=directory, capture_output=True, text=True, check=True
    )
    return completed.stdout.strip()


def _commit(directory: Path, path: str) -> str:
    target = directory / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        f"{path} {_git(directory, 'rev-parse', '--short', 'HEAD')}\n", encoding="utf-8"
    )
    _git(directory, "add", path)
    _git(directory, "commit", "-m", f"change {path}")
    return _git(directory, "rev-parse", "HEAD")


class Origin:
    """The repository a run fetches from, and the shallow clone the run starts in."""

    def __init__(self, root: Path) -> None:
        self.directory = root / "origin"
        self.directory.mkdir()
        _git(self.directory, "init", "-b", "main")
        _git(self.directory, "commit", "--allow-empty", "-m", "start")

    def commit(self, path: str) -> str:
        return _commit(self.directory, path)

    def clone(self, ref: str, depth: int) -> Path:
        clone = self.directory.parent / f"run-{ref.replace('/', '-')}"
        url = self.directory.as_uri()
        _git(
            self.directory.parent,
            "clone",
            "--quiet",
            "--depth",
            str(depth),
            "--branch",
            ref,
            url,
            str(clone),
        )
        return clone


def _decision(changes: Job, clone: Path, event: str, before: str) -> str:
    """What the changes step writes for the run in `clone`."""
    output = clone.parent / f"{clone.name}.output"
    environment = {
        "PATH": os.environ["PATH"],
        "HOME": str(clone.parent),
        "EVENT": event,
        "BEFORE": before,
        "DEFAULT_BRANCH": "main",
        "GITHUB_OUTPUT": str(output),
        "WEB_PATHS": _diff_step(changes)["env"]["WEB_PATHS"],
    }
    subprocess.run(
        ["bash", "-e", "-c", _diff_step(changes)["run"]],
        cwd=clone,
        env=environment,
        check=True,
        capture_output=True,
    )
    return output.read_text(encoding="utf-8").strip()


@pytest.fixture
def origin(tmp_path: Path) -> Origin:
    return Origin(tmp_path)


@needs_git_and_bash
def test_a_push_of_docs_only_does_not_run_the_job(changes: Job, origin: Origin):
    before = origin.commit("docs/guide.md")
    origin.commit("problems/0001/problem.md")
    clone = origin.clone("main", depth=2)
    assert _decision(changes, clone, "push", before) == "web=false"


@needs_git_and_bash
def test_a_push_that_changed_the_page_in_an_earlier_commit_runs_the_job(
    changes: Job, origin: Origin
):
    before = origin.commit("docs/guide.md")
    origin.commit("tools/web-ui/src/main.ts")
    origin.commit("docs/other.md")
    clone = origin.clone("main", depth=2)
    assert _decision(changes, clone, "push", before) == "web=true"


@needs_git_and_bash
def test_the_first_push_of_a_branch_is_compared_with_the_default_branch(
    changes: Job, origin: Origin
):
    origin.commit("docs/guide.md")
    _git(origin.directory, "switch", "-c", "feature")
    origin.commit("problems/0001/problem.md")
    clone = origin.clone("feature", depth=1)
    assert _decision(changes, clone, "push", NO_COMMIT) == "web=false"


@needs_git_and_bash
def test_the_first_push_of_a_branch_that_changed_the_page_runs_the_job(
    changes: Job, origin: Origin
):
    origin.commit("docs/guide.md")
    _git(origin.directory, "switch", "-c", "feature")
    origin.commit("cli/src/coding_study/entrypoints/web/app.py")
    clone = origin.clone("feature", depth=1)
    assert _decision(changes, clone, "push", NO_COMMIT) == "web=true"


@needs_git_and_bash
def test_a_push_whose_previous_commit_is_gone_falls_back_to_the_default_branch(
    changes: Job, origin: Origin
):
    origin.commit("docs/guide.md")
    clone = origin.clone("main", depth=1)
    assert _decision(changes, clone, "push", "1" * 40) == "web=false"


def _merged_pull_request(origin: Origin, changed: str) -> None:
    """A branch `merged` at the merge of a pull request that changed `changed`, into a main that
    has moved on since the pull request branched."""
    _git(origin.directory, "switch", "-c", "pull")
    origin.commit(changed)
    _git(origin.directory, "switch", "main")
    origin.commit("tools/web-ui/src/elsewhere.ts")
    _git(origin.directory, "switch", "-c", "merged")
    _git(origin.directory, "merge", "--no-ff", "-m", "merge", "pull")


@needs_git_and_bash
def test_a_pull_request_of_docs_only_does_not_run_the_job_whatever_main_changed(
    changes: Job, origin: Origin
):
    _merged_pull_request(origin, "docs/guide.md")
    clone = origin.clone("merged", depth=2)
    assert _decision(changes, clone, "pull_request", NO_COMMIT) == "web=false"


@needs_git_and_bash
def test_a_pull_request_that_changed_the_page_runs_the_job(changes: Job, origin: Origin):
    _merged_pull_request(origin, ".github/workflows/ci.yml")
    clone = origin.clone("merged", depth=2)
    assert _decision(changes, clone, "pull_request", NO_COMMIT) == "web=true"
