from pathlib import Path

from coding_study.application.verify_content import VerifyRequest, verify_content
from coding_study.application.verify_guides import GuideVerification, verify_guides
from tests.fakes import make_environment
from tests.guide_builders import write_guide, write_hashing, write_path

PROBLEMS = ("two-sum", "lru-cache", "tamper-evident-ledger")


def rows(root: Path) -> dict[str, tuple[str, ...]]:
    report = verify_content(make_environment(root), VerifyRequest(static_only=True), print)
    return {problem.directory: problem.static_errors for problem in report.problems}


def test_every_guide_and_path_passes_when_sound(content_root: Path):
    write_hashing(content_root)
    assert verify_guides(make_environment(content_root), PROBLEMS) == (
        GuideVerification("guides/hash-functions"),
        GuideVerification("guides/hash-maps"),
        GuideVerification("guides/paths/hashing.yaml"),
    )


def test_a_guide_that_does_not_load_reports_its_schema_issues(content_root: Path):
    write_guide(content_root, "broken", "Broken", level="expert")
    (found,) = verify_guides(make_environment(content_root), PROBLEMS)
    assert found.directory == "guides/broken"
    assert found.static_errors[0].startswith("guides/broken/meta.yaml: level: ")


def test_a_level_target_reads_the_problems_levels(content_root: Path):
    write_hashing(content_root)
    write_path(content_root, "too-far", ["{problem: tamper-evident-ledger, level: 5}"])
    found = verify_guides(make_environment(content_root), PROBLEMS)[-1]
    assert found == GuideVerification(
        "guides/paths/too-far.yaml",
        ("guides/paths/too-far.yaml: steps[0]: tamper-evident-ledger has 4 levels, not 5",),
    )


def test_verify_lists_the_guides_and_paths_after_the_problems(content_root: Path):
    write_hashing(content_root)
    found = rows(content_root)
    assert list(found)[-3:] == [
        "guides/hash-functions",
        "guides/hash-maps",
        "guides/paths/hashing.yaml",
    ]


def test_verify_of_chosen_problems_leaves_the_guides_out(content_root: Path):
    write_hashing(content_root)
    report = verify_content(
        make_environment(content_root), VerifyRequest(slugs=("two-sum",), static_only=True), print
    )
    assert [problem.directory for problem in report.problems] == ["problems/0001-two-sum"]


def test_a_broken_guide_fails_verify_as_a_static_failure(content_root: Path):
    write_guide(content_root, "hash-maps", "Hash maps", problems=("no-such-problem",))
    report = verify_content(make_environment(content_root), VerifyRequest(static_only=True), print)
    guide = next(row for row in report.problems if row.directory == "guides/hash-maps")
    assert (guide.passed, report.only_static_failures) == (False, True)


def test_s25_a_problem_names_guides_that_exist(content_root: Path):
    write_hashing(content_root)
    meta = content_root / "problems" / "0001-two-sum" / "meta.yaml"
    meta.write_text(f"{meta.read_text()}guides: [hash-maps, hash-tables]\n")
    errors = rows(content_root)["problems/0001-two-sum"]
    assert [error for error in errors if "guides" in error] == [
        'problems/0001-two-sum/meta.yaml: guides: "hash-tables" is not a guide'
    ]
