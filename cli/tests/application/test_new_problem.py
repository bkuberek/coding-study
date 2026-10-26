import shutil
from pathlib import Path

import pytest

from coding_study.adapters.fs_problem_files import FsProblemFiles
from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.adapters.problem_overlay import OverlayProblemFiles, OverlayProblemRepository
from coding_study.adapters.problem_templates import PackagedProblemTemplates
from coding_study.adapters.workspace_fs import WorkspaceFs
from coding_study.application.environment import ProblemDestination
from coding_study.application.new_problem import create_problem
from coding_study.application.verify_content import VerifyRequest, verify_content
from coding_study.domain.errors import UsageError
from coding_study.domain.problem import ContentStatus, Language, Track
from coding_study.domain.scaffold import WORKSPACE_FIRST_ID, ScaffoldRequest, TemplateName
from tests.fakes import make_environment
from tests.helpers import FIXTURE_TRACKS

TEMPLATES = PackagedProblemTemplates()
TEMPLATE_FILES = (
    "generator.py",
    "meta.yaml",
    "problem.md",
    "solutions/explanation.md",
    "tests.json",
)
REFERENCE_FILES = tuple(f"solutions/reference.{ext}" for ext in ("py", "ts", "java", "kt"))


@pytest.fixture
def environment(content_root: Path):
    return make_environment(content_root)


def create(environment, slug: str = "max-gap", template: TemplateName = TemplateName.ARRAY):
    return create_problem(environment, TEMPLATES, ScaffoldRequest(slug, template))


def replace_placeholders(directory: Path) -> None:
    for path in directory.rglob("*"):
        if path.is_file():
            path.write_text(path.read_text().replace("TODO", "Written"))


def static_errors(environment, slug: str) -> tuple[str, ...]:
    request = VerifyRequest(slugs=(slug,), static_only=True)
    return verify_content(environment, request, lambda _line: None).problems[0].static_errors


def test_creates_the_next_problem_directory(environment):
    assert create(environment).directory == "problems/0003-max-gap"


def test_writes_every_template_file_and_one_empty_reference_per_language(environment):
    assert create(environment).files == (*TEMPLATE_FILES, *REFERENCE_FILES)


def test_reference_files_are_empty(environment):
    create(environment)
    assert environment.workspace.read_text("problems/0003-max-gap/solutions/reference.kt") == ""


def test_the_problem_is_a_draft(environment):
    create(environment)
    assert environment.problems.load("max-gap").meta.status is ContentStatus.DRAFT


def test_the_signature_is_named_after_the_slug(environment):
    create(environment)
    assert environment.problems.load("max-gap").meta.signature.name == "maxGap"


def test_an_existing_slug_is_a_usage_error_naming_its_directory(environment):
    with pytest.raises(UsageError, match="problems/0001-two-sum"):
        create(environment, slug="two-sum")


@pytest.fixture
def workspace_destination(content_root: Path, tmp_path: Path):
    """Bundled content: `cstudy new` writes into the workspace's own problems/."""
    workspace = tmp_path / "workspace"
    destination = ProblemDestination(
        FsProblemFiles(workspace), WorkspaceFs(workspace), first_id=WORKSPACE_FIRST_ID
    )
    problems = OverlayProblemRepository(FsProblemRepository(content_root), workspace)
    files = OverlayProblemFiles(FsProblemFiles(content_root), workspace)
    overrides = {"problems": problems, "files": files, "new_problems": destination}
    return make_environment(content_root, **overrides), workspace


def test_a_workspace_problem_is_numbered_from_the_first_workspace_id(workspace_destination):
    environment, _ = workspace_destination
    assert create(environment).directory == f"problems/{WORKSPACE_FIRST_ID}-max-gap"


def test_a_workspace_problem_is_written_into_the_workspace(workspace_destination):
    environment, workspace = workspace_destination
    create(environment)
    assert (workspace / "problems" / f"{WORKSPACE_FIRST_ID}-max-gap" / "meta.yaml").is_file()


def test_a_workspace_problem_joins_the_catalog(workspace_destination):
    environment, _ = workspace_destination
    create(environment)
    assert environment.problems.load("max-gap").meta.id == str(WORKSPACE_FIRST_ID)


def test_a_catalog_slug_is_taken_for_a_workspace_problem_too(workspace_destination):
    environment, _ = workspace_destination
    with pytest.raises(UsageError, match="problems/0001-two-sum"):
        create(environment, slug="two-sum")


def test_a_slug_an_item_uses_is_a_usage_error_naming_its_directory(content_root):
    shutil.copytree(FIXTURE_TRACKS, content_root / "tracks")
    with pytest.raises(UsageError, match="tracks/system-design/url-shortener"):
        create(make_environment(content_root), slug="url-shortener")


def test_an_lld_problem_gets_a_rubric(environment):
    request = ScaffoldRequest("vending-machine", TemplateName.DESIGN, track=Track.LLD)
    assert "rubric.md" in create_problem(environment, TEMPLATES, request).files


def test_an_lld_problem_passes_static_checks_after_replacing_the_placeholders(environment):
    request = ScaffoldRequest("vending-machine", TemplateName.DESIGN, track=Track.LLD)
    created = create_problem(environment, TEMPLATES, request)
    replace_placeholders(environment.root / created.directory)
    assert static_errors(environment, "vending-machine") == ()


def test_an_existing_slug_writes_nothing(environment):
    with pytest.raises(UsageError):
        create(environment, slug="two-sum")
    assert not environment.workspace.exists("problems/0003-two-sum")


@pytest.mark.parametrize("template", list(TemplateName))
def test_each_template_fails_static_checks_until_the_placeholders_are_replaced(
    environment, template
):
    create(environment, "scaffolded", template)
    assert any("TODO" in error for error in static_errors(environment, "scaffolded"))


@pytest.mark.parametrize("template", list(TemplateName))
def test_each_template_passes_static_checks_after_replacing_the_placeholders(environment, template):
    created = create(environment, "scaffolded", template)
    replace_placeholders(environment.root / created.directory)
    assert static_errors(environment, "scaffolded") == ()


def test_the_concurrent_template_gets_an_empty_broken_reference_per_language(environment):
    created = create(environment, "limiter", TemplateName.CONCURRENT)
    broken = [name for name in created.files if name.startswith("solutions/broken/")]
    assert broken == [
        "solutions/broken/no-wait.java",
        "solutions/broken/no-wait.kt",
        "solutions/broken/no-wait.py",
    ]


def test_every_language_gets_a_reference_file_for_each_approach(environment):
    created = create(environment, "store", TemplateName.PROGRESSIVE)
    references = {name for name in created.files if name.startswith("solutions/reference.")}
    assert len(references) == len(Language)
