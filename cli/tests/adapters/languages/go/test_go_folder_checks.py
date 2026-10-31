"""The Go row of `cstudy doctor`
(docs/specs/installation-and-workspaces.md#cstudy-doctor-in-a-workspace)."""

from dataclasses import replace

from coding_study.adapters.languages.go.folder_checks import (
    GO_PROJECTS_CHECK,
    GoFolderChecks,
    go_folder_check,
)
from coding_study.adapters.languages.go.runner import GoRunner
from coding_study.application.ports import ProjectFolderChecks
from coding_study.domain.workspace_projects import GoProjectFolder

GO_WORK = "go 1.24\n\nuse .\n"


def go_folder(slug: str, **changes: object) -> GoProjectFolder:
    return replace(GoProjectFolder(f"projects/{slug}", slug, has_work_file=True), **changes)


def test_the_go_runner_checks_its_project_folders():
    assert issubclass(GoRunner, ProjectFolderChecks)


def test_go_folders_with_their_go_work_and_own_modules_pass():
    assert go_folder_check((go_folder("a-project-go"),)).failing == ()


def test_a_go_folder_without_its_go_work_is_a_problem_doctor_fix_repairs():
    check = go_folder_check((go_folder("a-project-go", has_work_file=False),))
    assert (check.name, check.failing, check.problem, check.fix) == (
        GO_PROJECTS_CHECK,
        ("projects/a-project-go has no go.work",),
        "problem",
        None,
    )


def test_a_go_replacement_that_does_not_resolve_points_to_the_restore():
    check = go_folder_check((go_folder("a-project-go", unresolved=("../../gone",)),))
    assert check.fix == "cstudy start a-project-go --restore go.mod"


def test_two_go_folders_with_one_module_say_so():
    folders = (go_folder("a-project-go", module="bank"), go_folder("b-project-go", module="bank"))
    check = go_folder_check(folders)
    assert (check.failing, check.fix) == (
        ("projects/a-project-go and projects/b-project-go both declare module bank",),
        "give each folder a module of its own in its go.mod",
    )


def test_several_problems_are_counted_as_problems_and_shown_apart_from_their_commas():
    folders = (go_folder("a-project-go", has_work_file=False), go_folder("b-project-go"))
    folders = (*folders, go_folder("c-project-go", module="b-project-go"))
    check = go_folder_check(folders)
    assert (len(check.failing), check.problem, check.separator) == (2, "problems", "; ")


def test_a_workspace_folder_without_its_go_work_fails_the_check(tmp_path):
    folder = tmp_path / "projects/bank-project-go"
    folder.mkdir(parents=True)
    (folder / "go.mod").write_text("module bank-project-go\n\ngo 1.24\n")
    (check,) = GoFolderChecks(tmp_path).folder_checks()
    assert check.failing == ("projects/bank-project-go has no go.work",)


def test_repair_writes_the_missing_go_work_files_and_names_them(tmp_path):
    folder = tmp_path / "projects/bank-project-go"
    folder.mkdir(parents=True)
    (folder / "go.mod").write_text("module bank-project-go\n\ngo 1.24\n")
    written = GoFolderChecks(tmp_path).repair_folders()
    assert (written, (folder / "go.work").read_text()) == (
        ("projects/bank-project-go/go.work",),
        GO_WORK,
    )
