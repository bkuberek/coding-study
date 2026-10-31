"""The generated test files of a project attempt: each level's file is written once, when the
level opens, and never over a file that exists
(docs/specs/problem-format.md#generated-test-files)."""

import pytest

from coding_study.adapters.workspace_fs import WorkspaceFs
from coding_study.application.project_tests import LevelTestFile, LevelTestWriter
from coding_study.domain.project_tests import LevelTests
from tests.project_builders import ops_case, project_problem

ROOT = "projects/bank-project-python"
PROBLEM = project_problem(
    ops_case("ex1", 1, ("deposit", [1, "a", 5], -1)),
    ops_case("ex2", 1, ("deposit", [2, "b", 5], -1)),
    ops_case("h1", 1, ("deposit", [3, "c", 5], -1), visible=False),
    ops_case("ex3", 2, ("transfer", [4, "a", "b", 5], -1)),
)
LEVEL_1 = f"{ROOT}/tests/test_level_1.py"
LEVEL_2 = f"{ROOT}/tests/test_level_2.py"


class RecordingGenerator:
    def __init__(self) -> None:
        self.generated: list[LevelTests] = []

    def generate(self, tests: LevelTests) -> str:
        self.generated.append(tests)
        return f"# level {tests.level}\n"


@pytest.fixture
def workspace(tmp_path) -> WorkspaceFs:
    return WorkspaceFs(tmp_path)


@pytest.fixture
def generator() -> RecordingGenerator:
    return RecordingGenerator()


@pytest.fixture
def writer(workspace, generator) -> LevelTestWriter:
    return LevelTestWriter(workspace, generator)


def test_a_level_file_is_written_in_the_project_tests_directory(writer, workspace):
    writer.write_level(PROBLEM, ROOT, 1)
    assert workspace.read_text(LEVEL_1) == "# level 1\n"


def test_writing_a_level_reports_the_file_its_tests_and_that_it_was_written(writer):
    assert writer.write_level(PROBLEM, ROOT, 1) == LevelTestFile(
        level=1, path="tests/test_level_1.py", tests=2, written=True
    )


def test_the_generator_spells_the_tests_of_that_level(writer, generator):
    writer.write_level(PROBLEM, ROOT, 2)
    assert [test.case_id for test in generator.generated[0].tests] == ["ex3"]


def test_opening_a_level_writes_only_its_own_file(writer, workspace):
    writer.write_level(PROBLEM, ROOT, 2)
    assert not workspace.exists(LEVEL_1)


def test_a_file_that_exists_is_kept_as_the_user_left_it(writer, workspace):
    workspace.write_text(LEVEL_1, "# mine\n")
    writer.write_level(PROBLEM, ROOT, 1)
    assert workspace.read_text(LEVEL_1) == "# mine\n"


def test_a_kept_file_is_reported_as_not_written(writer, workspace):
    workspace.write_text(LEVEL_1, "# mine\n")
    assert not writer.write_level(PROBLEM, ROOT, 1).written


def test_a_kept_file_costs_no_generation(writer, workspace, generator):
    workspace.write_text(LEVEL_1, "# mine\n")
    writer.write_level(PROBLEM, ROOT, 1)
    assert generator.generated == []


def test_resuming_writes_back_the_missing_files_of_the_unlocked_levels(writer, workspace):
    workspace.write_text(LEVEL_1, "# mine\n")
    written = writer.write_levels(PROBLEM, ROOT, 2)
    assert [(file.level, file.written) for file in written] == [(1, False), (2, True)]


def test_resuming_writes_no_file_of_a_locked_level(writer, workspace):
    writer.write_levels(PROBLEM, ROOT, 1)
    assert not workspace.exists(LEVEL_2)


def test_a_level_the_problem_lacks_is_rejected(writer):
    with pytest.raises(ValueError, match="bank-project-python has no level 3"):
        writer.write_level(PROBLEM, ROOT, 3)
