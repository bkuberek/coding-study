import shutil
from pathlib import Path

import pytest

from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.domain.errors import ContentError, UnknownProblemError
from coding_study.domain.problem import Language, ProblemKind, ProblemSummary
from tests.fakes import repository_root
from tests.helpers import PROJECT_PROBLEMS, numbered_directory

TWO_SUM = Path("problems/two-sum")


def issues_for(content_root: Path, slug: str = "two-sum") -> list[str]:
    with pytest.raises(ContentError) as raised:
        FsProblemRepository(content_root).load(slug)
    return [str(issue) for issue in raised.value.issues]


def test_loads_problem_by_slug(content_root):
    problem = FsProblemRepository(content_root).load("two-sum")
    assert (problem.meta.slug, len(problem.cases)) == ("two-sum", 4)


def test_loads_class_kind_problem(content_root):
    problem = FsProblemRepository(content_root).load("lru-cache")
    assert problem.meta.kind == ProblemKind.DESIGN


def test_unknown_slug_is_reported(content_root):
    with pytest.raises(UnknownProblemError, match='unknown problem "three-sum"'):
        FsProblemRepository(content_root).load("three-sum")


def test_slug_must_match_the_whole_directory_name(content_root):
    with pytest.raises(UnknownProblemError):
        FsProblemRepository(content_root).load("sum")


def test_missing_problems_directory_means_unknown_slug(content_root):
    shutil.rmtree(content_root / "problems")
    with pytest.raises(UnknownProblemError):
        FsProblemRepository(content_root).load("two-sum")


def test_schema_violations_name_the_file(content_root):
    meta = content_root / TWO_SUM / "meta.yaml"
    meta.write_text(meta.read_text().replace("status: ready", "status: done"))
    assert issues_for(content_root) == [
        f"{TWO_SUM}/meta.yaml: status: 'done' is not one of ['draft', 'ready']"
    ]


def test_meta_and_tests_violations_are_reported_together(content_root):
    meta = content_root / TWO_SUM / "meta.yaml"
    meta.write_text(meta.read_text().replace("status: ready", "status: done"))
    tests = content_root / TWO_SUM / "tests.json"
    tests.write_text(tests.read_text().replace('"version": 1', '"version": 2'))
    assert len(issues_for(content_root)) == 2


def test_malformed_yaml_reports_line(content_root):
    (content_root / TWO_SUM / "meta.yaml").write_text("slug: [two-sum\n")
    [issue] = issues_for(content_root)
    assert issue.startswith(f"{TWO_SUM}/meta.yaml: line 2")


def test_malformed_json_reports_line_and_column(content_root):
    (content_root / TWO_SUM / "tests.json").write_text('{"version": 1,\n "cases": [}\n')
    [issue] = issues_for(content_root)
    assert issue.startswith(f"{TWO_SUM}/tests.json: line 2, column 12:")


def test_missing_file_is_reported(content_root):
    (content_root / TWO_SUM / "tests.json").unlink()
    assert issues_for(content_root) == [f"{TWO_SUM}/tests.json: file not found"]


def test_directory_name_must_match_the_slug(content_root):
    (content_root / TWO_SUM).rename(content_root / "problems" / "word-break")
    assert issues_for(content_root, "word-break") == [
        "problems/word-break/meta.yaml: slug: directory name word-break does not match slug two-sum"
    ]


def test_a_numbered_directory_is_not_a_problem(content_root):
    (content_root / TWO_SUM).rename(content_root / "problems" / numbered_directory(7, "two-sum"))
    assert FsProblemRepository(content_root).slugs() == ("lru-cache",)


def test_invalid_type_dsl_is_a_content_error(content_root):
    meta = content_root / TWO_SUM / "meta.yaml"
    meta.write_text(meta.read_text().replace('type: "int[]"}', 'type: "int[}"}', 1))
    assert issues_for(content_root) == [
        f'{TWO_SUM}/meta.yaml: signature.function.params[0].type: invalid type "int[}}": '
        'expected "]" at column 5'
    ]


def slugs(summaries: tuple[ProblemSummary, ...]) -> list[str]:
    return [summary.meta.slug for summary in summaries]


def test_lists_problems_in_directory_name_order(content_root):
    assert slugs(FsProblemRepository(content_root).list_summaries()) == ["lru-cache", "two-sum"]


def test_summary_names_the_problem_directory(content_root):
    [_, two_sum] = FsProblemRepository(content_root).list_summaries()
    assert two_sum.directory == "problems/two-sum"


def test_reference_languages_come_from_files_of_declared_approaches(content_root):
    solutions = content_root / TWO_SUM / "solutions"
    solutions.mkdir()
    for name in ("hash-map.kt", "brute-force.py", "explanation.md", "unknown.ts"):
        (solutions / name).write_text("")
    [_, two_sum] = FsProblemRepository(content_root).list_summaries()
    assert two_sum.reference_languages == (Language.PYTHON, Language.KOTLIN)


def test_problem_without_solutions_has_no_reference_languages(content_root):
    [_, two_sum] = FsProblemRepository(content_root).list_summaries()
    assert two_sum.reference_languages == ()


def test_listing_skips_entries_that_are_not_problem_directories(content_root):
    (content_root / "problems" / "README.md").write_text("")
    (content_root / "problems" / numbered_directory(7, "drafts")).mkdir()
    assert len(FsProblemRepository(content_root).list_summaries()) == 2


def test_listing_does_not_need_tests_json(content_root):
    (content_root / TWO_SUM / "tests.json").unlink()
    assert len(FsProblemRepository(content_root).list_summaries()) == 2


def test_listing_without_problems_directory_is_empty(content_root):
    shutil.rmtree(content_root / "problems")
    assert FsProblemRepository(content_root).list_summaries() == ()


def test_listing_reports_every_invalid_meta(content_root):
    for directory in ("two-sum", "lru-cache"):
        meta = content_root / "problems" / directory / "meta.yaml"
        meta.write_text(meta.read_text().replace("status: ready", "status: done"))
    with pytest.raises(ContentError) as raised:
        FsProblemRepository(content_root).list_summaries()
    assert len(raised.value.issues) == 2


def test_problems_can_live_in_another_directory(content_root):
    (content_root / "runners").mkdir()
    (content_root / "problems").rename(content_root / "runners" / "conformance")
    repository = FsProblemRepository(content_root, "runners/conformance")
    assert repository.load("two-sum").meta.directory_name == "two-sum"


def test_a_project_problem_loads_its_starter_and_reference(tmp_path):
    root = repository_root(tmp_path, PROJECT_PROBLEMS)
    project_files = FsProblemRepository(root).load("bank-project-python").project_files
    assert project_files is not None
    assert (project_files.starter is not None, set(project_files.overlays)) == (True, {"reference"})


def test_a_project_problem_with_a_link_in_its_starter_does_not_load(tmp_path):
    root = repository_root(tmp_path, PROJECT_PROBLEMS)
    starter = root / "problems" / "bank-project-python" / "starter"
    (starter / "link.md").symlink_to("README.md")
    with pytest.raises(ContentError, match=r"starter/link\.md: is a symbolic link"):
        FsProblemRepository(root).load("bank-project-python")


def test_other_problems_have_no_project_files(content_root):
    assert FsProblemRepository(content_root).load("lru-cache").project_files is None


def test_a_project_reference_is_its_overlay_in_the_problems_language(tmp_path):
    root = repository_root(tmp_path, PROJECT_PROBLEMS)
    [bank] = FsProblemRepository(root).list_summaries()
    assert bank.reference_languages == (Language.PYTHON,)


def test_a_project_without_files_in_its_overlay_has_no_reference_languages(tmp_path):
    root = repository_root(tmp_path, PROJECT_PROBLEMS)
    overlay = root / "problems" / "bank-project-python" / "solutions" / "reference"
    shutil.rmtree(overlay)
    overlay.mkdir()
    [bank] = FsProblemRepository(root).list_summaries()
    assert bank.reference_languages == ()
