import shutil
from pathlib import Path

import pytest

from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.domain.errors import ContentError, UnknownProblemError
from coding_study.domain.problem import Language, ProblemKind, ProblemSummary

TWO_SUM = Path("problems/0001-two-sum")


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


def test_slug_must_match_the_whole_directory_suffix(content_root):
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
    (content_root / TWO_SUM / "meta.yaml").write_text('id: "0001"\nslug: [two-sum\n')
    [issue] = issues_for(content_root)
    assert issue.startswith(f"{TWO_SUM}/meta.yaml: line 3")


def test_malformed_json_reports_line_and_column(content_root):
    (content_root / TWO_SUM / "tests.json").write_text('{"version": 1,\n "cases": [}\n')
    [issue] = issues_for(content_root)
    assert issue.startswith(f"{TWO_SUM}/tests.json: line 2, column 12:")


def test_missing_file_is_reported(content_root):
    (content_root / TWO_SUM / "tests.json").unlink()
    assert issues_for(content_root) == [f"{TWO_SUM}/tests.json: file not found"]


def test_directory_name_must_match_id_and_slug(content_root):
    (content_root / TWO_SUM).rename(content_root / "problems" / "0007-two-sum")
    assert issues_for(content_root) == [
        "problems/0007-two-sum/meta.yaml: id: directory name 0007-two-sum does not match "
        "id and slug (expected 0001-two-sum)"
    ]


def test_invalid_type_dsl_is_a_content_error(content_root):
    meta = content_root / TWO_SUM / "meta.yaml"
    meta.write_text(meta.read_text().replace('type: "int[]"}', 'type: "int[}"}', 1))
    assert issues_for(content_root) == [
        f'{TWO_SUM}/meta.yaml: signature.function.params[0].type: invalid type "int[}}": '
        'expected "]" at column 5'
    ]


def slugs(summaries: tuple[ProblemSummary, ...]) -> list[str]:
    return [summary.meta.slug for summary in summaries]


def test_lists_problems_in_id_order(content_root):
    assert slugs(FsProblemRepository(content_root).list_summaries()) == ["two-sum", "lru-cache"]


def test_summary_names_the_problem_directory(content_root):
    [two_sum, _] = FsProblemRepository(content_root).list_summaries()
    assert two_sum.directory == "problems/0001-two-sum"


def test_reference_languages_come_from_files_of_declared_approaches(content_root):
    solutions = content_root / TWO_SUM / "solutions"
    solutions.mkdir()
    for name in ("hash-map.kt", "brute-force.py", "explanation.md", "unknown.ts"):
        (solutions / name).write_text("")
    [two_sum, _] = FsProblemRepository(content_root).list_summaries()
    assert two_sum.reference_languages == (Language.PYTHON, Language.KOTLIN)


def test_problem_without_solutions_has_no_reference_languages(content_root):
    [two_sum, _] = FsProblemRepository(content_root).list_summaries()
    assert two_sum.reference_languages == ()


def test_listing_skips_entries_that_are_not_problem_directories(content_root):
    (content_root / "problems" / "README.md").write_text("")
    (content_root / "problems" / "drafts").mkdir()
    assert len(FsProblemRepository(content_root).list_summaries()) == 2


def test_listing_does_not_need_tests_json(content_root):
    (content_root / TWO_SUM / "tests.json").unlink()
    assert len(FsProblemRepository(content_root).list_summaries()) == 2


def test_listing_without_problems_directory_is_empty(content_root):
    shutil.rmtree(content_root / "problems")
    assert FsProblemRepository(content_root).list_summaries() == ()


def test_listing_reports_every_invalid_meta(content_root):
    for directory in ("0001-two-sum", "0002-lru-cache"):
        meta = content_root / "problems" / directory / "meta.yaml"
        meta.write_text(meta.read_text().replace("status: ready", "status: done"))
    with pytest.raises(ContentError) as raised:
        FsProblemRepository(content_root).list_summaries()
    assert len(raised.value.issues) == 2


def test_problems_can_live_in_another_directory(content_root):
    (content_root / "runners").mkdir()
    (content_root / "problems").rename(content_root / "runners" / "conformance")
    repository = FsProblemRepository(content_root, "runners/conformance")
    assert repository.load("two-sum").meta.directory_name == "0001-two-sum"
