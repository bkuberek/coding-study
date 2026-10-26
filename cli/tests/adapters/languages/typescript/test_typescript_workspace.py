"""A user's practice file runs from the workspace project the way `cstudy test` runs it."""

import shutil
from pathlib import Path

import pytest
import yaml

from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.typescript import create_runner
from coding_study.adapters.problem_documents import meta_from_document
from coding_study.adapters.runner_runtime import RUNTIME_RUNNERS
from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.application.ports import Prepared, UserCode
from coding_study.domain.cases import FunctionInput
from coding_study.domain.layout import stub_path, user_target
from coding_study.domain.naming import symbol_names
from coding_study.domain.problem import Language
from coding_study.domain.runs import CaseOutcome, Raised, Returned, RunCase, RunJob, RunRequest
from tests.helpers import REPOSITORY_ROOT, WORKSPACE_TEMPLATE
from tests.stub_contract import GOLDEN_ROOT, SIGNATURES_DIRECTORY

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed"),
]

TYPESCRIPT = Language.TYPESCRIPT
HANG_GUARD_MS = 5_000
INVERT_TREE = meta_from_document(
    yaml.safe_load((SIGNATURES_DIRECTORY / "invert-tree.yaml").read_text()), "invert-tree.yaml"
)
SOLUTION = """\
import { TreeNode } from "#support";

export function invertTree(root: TreeNode | null): TreeNode | null {
  if (root === null) {
    return null;
  }
  return new TreeNode(root.val, invertTree(root.right), invertTree(root.left));
}
"""


def mirror_workspace(root: Path) -> Path:
    """`root` as a workspace: the template's TypeScript project files, and the real runners as
    its runner runtime."""
    runtime = root / RUNTIME_RUNNERS
    runtime.parent.mkdir(parents=True)
    runtime.symlink_to(REPOSITORY_ROOT / "runners")
    project = root / "typescript"
    (project / "practice").mkdir(parents=True)
    for name in ("package.json", "support.ts"):
        shutil.copyfile(WORKSPACE_TEMPLATE / "typescript" / name, project / name)
    return root


def run_user_code(root: Path, tree: list[int | None]) -> CaseOutcome:
    prepared = create_runner(LanguageContext(root, root / RUNTIME_RUNNERS)).prepare(
        UserCode(INVERT_TREE), print
    )
    assert isinstance(prepared, Prepared)
    job = RunJob(
        job_id=INVERT_TREE.slug,
        kind=INVERT_TREE.kind,
        target=user_target(INVERT_TREE, TYPESCRIPT, str(root)),
        names=symbol_names(INVERT_TREE.signature, TYPESCRIPT),
        signature=INVERT_TREE.signature,
        cases=(RunCase("ex1", FunctionInput({"root": list(tree)}), HANG_GUARD_MS),),
    )
    report = SubprocessRunner(root / ".cs" / "runs").run(prepared.launch, RunRequest((job,)))
    return report.job(INVERT_TREE.slug).cases[0].outcome


def test_practice_file_imports_support_classes_through_the_workspace(tmp_path):
    root = mirror_workspace(tmp_path)
    (root / stub_path(INVERT_TREE, TYPESCRIPT)).write_text(SOLUTION)
    result = run_user_code(root, [4, 2, 7, 1, 3, 6, 9])
    assert isinstance(result, Returned), result
    assert result.output == [4, 7, 2, 9, 6, 3, 1]


def test_generated_stub_reports_not_implemented(tmp_path):
    root = mirror_workspace(tmp_path)
    shutil.copyfile(
        GOLDEN_ROOT / "typescript" / "invert-tree.ts", root / stub_path(INVERT_TREE, TYPESCRIPT)
    )
    result = run_user_code(root, [1])
    assert isinstance(result, Raised), result
    assert result.error.message == "Not implemented"
