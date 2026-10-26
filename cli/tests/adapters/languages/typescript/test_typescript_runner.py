import json
from pathlib import Path

import pytest
import yaml

from coding_study.adapters.languages.typescript.runner import (
    MAX_DIAGNOSTIC_LINES,
    TypeScriptRunner,
    user_file_diagnostics,
)
from coding_study.adapters.problem_documents import meta_from_document
from coding_study.application.ports import (
    BuildFailed,
    Prepared,
    ProbeResult,
    References,
    ReferenceSource,
    UserCode,
)
from coding_study.domain.errors import ContentError, RunnerStartError
from coding_study.domain.problem import Language
from coding_study.domain.runs import HELLO_TIMEOUT_MS
from tests.stub_contract import SIGNATURES_DIRECTORY

TWO_SUM = meta_from_document(
    yaml.safe_load((SIGNATURES_DIRECTORY / "two-sum.yaml").read_text()), "two-sum.yaml"
)
USER_FILE = "practice/two-sum.ts"
TYPE_ERROR = f"{USER_FILE}(3,5): error TS2322: Type 'string' is not assignable to type 'number'."


PASSED = ProbeResult(0, "")


class FakeTypeChecker:
    def __init__(self, result: ProbeResult | None = PASSED) -> None:
        self.result = result
        self.projects: list[Path] = []

    def check(self, project: Path) -> ProbeResult | None:
        self.projects.append(project)
        return self.result


def no_notice(message: str) -> None:
    raise AssertionError(f"unexpected notice: {message}")


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A repository root with the TypeScript runner and an installed workspace."""
    (tmp_path / "runners" / "typescript").mkdir(parents=True)
    (tmp_path / "runners" / "typescript" / "runner.ts").write_text("")
    workspace = tmp_path / "typescript"
    (workspace / "node_modules").mkdir(parents=True)
    (workspace / "package.json").write_text("{}")
    return tmp_path


def prepared(root: Path, scope: UserCode | References, checker: FakeTypeChecker) -> Prepared:
    result = TypeScriptRunner(root, root / "runners", checker).prepare(scope, no_notice)
    assert isinstance(result, Prepared)
    return result


def reference_source(directory: Path, approach_id: str, text: str) -> ReferenceSource:
    path = directory / f"{approach_id}.ts"
    path.write_text(text)
    return ReferenceSource(approach_id, path)


def test_user_code_launches_node_on_the_runner_script(root):
    launch = prepared(root, UserCode(TWO_SUM), FakeTypeChecker()).launch
    assert launch.command == ("node", str(root / "runners" / "typescript" / "runner.ts"))


def test_user_code_runs_in_the_workspace_project(root):
    launch = prepared(root, UserCode(TWO_SUM), FakeTypeChecker()).launch
    assert launch.cwd == root / "typescript"


def test_launch_uses_the_typescript_hello_timeout(root):
    launch = prepared(root, UserCode(TWO_SUM), FakeTypeChecker()).launch
    assert launch.hello_timeout_ms == HELLO_TIMEOUT_MS[Language.TYPESCRIPT]


def test_user_code_without_typecheck_builds_nothing(root):
    checker = FakeTypeChecker()
    result = prepared(root, UserCode(TWO_SUM), checker)
    assert (result.build_note, checker.projects) == (None, [])


def test_typecheck_runs_in_the_workspace_project(root):
    checker = FakeTypeChecker()
    prepared(root, UserCode(TWO_SUM, typecheck=True), checker)
    assert checker.projects == [root / "typescript"]


def test_passing_typecheck_notes_tsc(root):
    assert prepared(root, UserCode(TWO_SUM, typecheck=True), FakeTypeChecker()).build_note == "tsc"


def test_failing_typecheck_reports_the_user_file_diagnostics(root):
    checker = FakeTypeChecker(ProbeResult(2, f"{TYPE_ERROR}\n"))
    result = TypeScriptRunner(root, root / "runners", checker).prepare(
        UserCode(TWO_SUM, typecheck=True), no_notice
    )
    assert result == BuildFailed((TYPE_ERROR,))


def test_type_errors_only_in_other_files_do_not_block(root):
    other = "practice/lru-cache.ts(1,1): error TS1005: ';' expected."
    checker = FakeTypeChecker(ProbeResult(2, f"{other}\n"))
    assert prepared(root, UserCode(TWO_SUM, typecheck=True), checker).build_note == "tsc"


def test_typecheck_without_installed_dependencies_is_a_start_error(root):
    (root / "typescript" / "node_modules").rmdir()
    with pytest.raises(RunnerStartError, match="pnpm install"):
        TypeScriptRunner(root, root / "runners", FakeTypeChecker()).prepare(
            UserCode(TWO_SUM, typecheck=True), no_notice
        )


def test_typecheck_without_pnpm_is_a_start_error(root):
    with pytest.raises(RunnerStartError, match="pnpm"):
        TypeScriptRunner(root, root / "runners", FakeTypeChecker(None)).prepare(
            UserCode(TWO_SUM, typecheck=True), no_notice
        )


def test_missing_workspace_project_is_a_start_error(root):
    (root / "typescript" / "package.json").unlink()
    with pytest.raises(RunnerStartError, match="typescript"):
        TypeScriptRunner(root, root / "runners", FakeTypeChecker()).prepare(
            UserCode(TWO_SUM), no_notice
        )


def test_missing_runner_script_is_a_start_error(root):
    (root / "runners" / "typescript" / "runner.ts").unlink()
    with pytest.raises(RunnerStartError, match=r"runners/typescript/runner\.ts"):
        TypeScriptRunner(root, root / "runners", FakeTypeChecker()).prepare(
            UserCode(TWO_SUM), no_notice
        )


def test_references_are_copied_to_their_build_path(root, tmp_path):
    source = reference_source(tmp_path, "hash-map", "export const marker = 1;\n")
    prepared(root, References(TWO_SUM, (source,)), FakeTypeChecker())
    copy = root / ".cs" / "build" / "typescript" / "ref" / "two-sum" / "hash-map.ts"
    assert copy.read_text() == "export const marker = 1;\n"


def test_reference_build_project_maps_support_like_the_workspace(root, tmp_path):
    prepared(root, References(TWO_SUM, ()), FakeTypeChecker())
    package = json.loads((root / ".cs" / "build" / "typescript" / "package.json").read_text())
    assert (package["type"], package["imports"]) == ("module", {"#support": "./support.ts"})


def test_reference_build_support_reexports_the_runner_support(root):
    prepared(root, References(TWO_SUM, ()), FakeTypeChecker())
    support = (root / ".cs" / "build" / "typescript" / "support.ts").read_text()
    assert 'export * from "../../../runners/typescript/support.ts";' in support


def test_references_launch_in_the_build_project(root):
    launch = prepared(root, References(TWO_SUM, ()), FakeTypeChecker()).launch
    assert launch.cwd == root / ".cs" / "build" / "typescript"


def test_references_do_not_need_the_workspace(root):
    (root / "typescript" / "package.json").unlink()
    assert prepared(root, References(TWO_SUM, ()), FakeTypeChecker()).build_note is None


def test_missing_reference_file_is_a_content_error(root, tmp_path):
    missing = ReferenceSource("hash-map", tmp_path / "hash-map.ts")
    with pytest.raises(ContentError, match=r"hash-map\.ts"):
        TypeScriptRunner(root, root / "runners", FakeTypeChecker()).prepare(
            References(TWO_SUM, (missing,)), no_notice
        )


def test_diagnostics_keep_continuation_lines_of_the_user_file():
    output = f"{TYPE_ERROR}\n  Details of the error.\nother.ts(1,1): error TS1\n  Other details.\n"
    assert user_file_diagnostics(output, USER_FILE) == (TYPE_ERROR, "  Details of the error.")


def test_diagnostics_are_capped():
    output = "\n".join([TYPE_ERROR] * (MAX_DIAGNOSTIC_LINES + 5))
    assert len(user_file_diagnostics(output, USER_FILE)) == MAX_DIAGNOSTIC_LINES
