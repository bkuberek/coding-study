import re
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
from coding_study.domain import scaffold
from coding_study.domain.cases import OperationSequence
from coding_study.domain.concurrency import ConcurrencyModel, ThreadKind
from coding_study.domain.errors import UsageError
from coding_study.domain.problem import ALL_LANGUAGES, ContentStatus, Language, ProblemKind, Track
from coding_study.domain.project import RUST_CLOCK_CRATES
from coding_study.domain.project_checks import jvm_build_files
from coding_study.domain.scaffold import (
    WORKSPACE_FIRST_ID,
    ScaffoldRequest,
    TemplateName,
    render_template,
)
from coding_study.domain.signature import ClassSignature
from coding_study.domain.stress import StressScenario
from coding_study.domain.virtual_clock import ProjectClock
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
EXTENSIONS = ("py", "ts", "java", "kt", "go", "rs")
REFERENCE_FILES = tuple(f"solutions/reference.{extension}" for extension in EXTENSIONS)


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


ONE_LANGUAGE_TEMPLATES = (
    TemplateName.CONCURRENT,
    TemplateName.PROJECT_PYTHON,
    TemplateName.PROJECT_TYPESCRIPT,
    TemplateName.PROJECT_JAVA,
    TemplateName.PROJECT_KOTLIN,
    TemplateName.PROJECT_GO,
    TemplateName.PROJECT_RUST,
)


@pytest.mark.parametrize("template", [t for t in TemplateName if t not in ONE_LANGUAGE_TEMPLATES])
def test_each_template_writes_its_languages_explicitly(environment, template):
    created = create(environment, "scaffolded", template)
    meta = (environment.root / created.directory / "meta.yaml").read_text()
    assert "languages: [python, typescript, java, kotlin, go, rust]\n" in meta


def test_the_concurrent_template_gets_an_empty_broken_reference_per_language(environment):
    created = create(environment, "limiter", TemplateName.CONCURRENT)
    broken = [name for name in created.files if name.startswith("solutions/broken/")]
    assert broken == [
        "solutions/broken/no-wait.java",
        "solutions/broken/no-wait.kt",
        "solutions/broken/no-wait.py",
        "solutions/broken/no-wait.go",
        "solutions/broken/no-wait.rs",
    ]


def test_every_language_gets_a_reference_file_for_each_approach(environment):
    created = create(environment, "store", TemplateName.PROGRESSIVE)
    references = {name for name in created.files if name.startswith("solutions/reference.")}
    assert len(references) == len(ALL_LANGUAGES)


PROJECT_FILES = (
    "meta.yaml",
    "problem.md",
    "solutions/explanation.md",
    "solutions/reference/app/main.py",
    "starter/README.md",
    "starter/app/main.py",
    "starter/pyproject.toml",
    "tests.json",
)


def test_a_python_project_gets_its_starter_and_overlay_and_no_reference_file(environment):
    created = create(environment, "bank-project-python", TemplateName.PROJECT_PYTHON)
    assert created.files == PROJECT_FILES


def test_a_python_project_lists_python_alone(environment):
    created = create(environment, "bank-project-python", TemplateName.PROJECT_PYTHON)
    meta = environment.problems.load(created.slug).meta
    assert (meta.kind, meta.languages) == (ProblemKind.PROJECT, (Language.PYTHON,))


def test_a_python_projects_starter_declares_level_ones_method_only(environment):
    created = create(environment, "bank-project-python", TemplateName.PROJECT_PYTHON)
    entry = (environment.root / created.directory / "starter" / "app" / "main.py").read_text()
    assert ("class BankProjectPython:" in entry, "def put(" in entry, "def get(" in entry) == (
        True,
        True,
        False,
    )


def test_a_python_projects_overlay_implements_every_level(environment):
    created = create(environment, "bank-project-python", TemplateName.PROJECT_PYTHON)
    overlay = environment.root / created.directory / "solutions" / "reference" / "app" / "main.py"
    assert ("def put(" in overlay.read_text(), "def get(" in overlay.read_text()) == (True, True)


TYPESCRIPT_PROJECT_FILES = (
    "meta.yaml",
    "problem.md",
    "solutions/explanation.md",
    "solutions/reference/src/main.ts",
    "starter/README.md",
    "starter/package.json",
    "starter/src/main.ts",
    "starter/tsconfig.json",
    "tests.json",
)


def test_a_typescript_project_gets_its_starter_and_overlay_and_no_reference_file(environment):
    created = create(environment, "bank-project-typescript", TemplateName.PROJECT_TYPESCRIPT)
    assert created.files == TYPESCRIPT_PROJECT_FILES


def test_a_typescript_project_lists_typescript_alone(environment):
    created = create(environment, "bank-project-typescript", TemplateName.PROJECT_TYPESCRIPT)
    meta = environment.problems.load(created.slug).meta
    assert (meta.kind, meta.languages) == (ProblemKind.PROJECT, (Language.TYPESCRIPT,))


def test_a_typescript_projects_starter_declares_level_ones_method_only(environment):
    created = create(environment, "bank-project-typescript", TemplateName.PROJECT_TYPESCRIPT)
    entry = (environment.root / created.directory / "starter" / "src" / "main.ts").read_text()
    assert (
        "export class BankProjectTypescript {" in entry,
        "  put(" in entry,
        "  get(" in entry,
    ) == (True, True, False)


def test_a_typescript_projects_overlay_implements_every_level(environment):
    created = create(environment, "bank-project-typescript", TemplateName.PROJECT_TYPESCRIPT)
    overlay = environment.root / created.directory / "solutions" / "reference" / "src" / "main.ts"
    assert ("  put(" in overlay.read_text(), "  get(" in overlay.read_text()) == (True, True)


JVM_TEMPLATES = {
    Language.JAVA: TemplateName.PROJECT_JAVA,
    Language.KOTLIN: TemplateName.PROJECT_KOTLIN,
}
JVM_EXTENSIONS = {Language.JAVA: "java", Language.KOTLIN: "kt"}


def jvm_project(environment, language: Language):
    return create(environment, f"bank-project-{language}", JVM_TEMPLATES[language])


def jvm_entry(language: Language, class_name: str) -> str:
    return f"src/main/{language}/app/{class_name}.{JVM_EXTENSIONS[language]}"


@pytest.mark.parametrize("language", [Language.JAVA, Language.KOTLIN])
def test_a_jvm_project_gets_its_starter_and_overlay_and_no_reference_file(environment, language):
    entry = jvm_entry(language, f"BankProject{language.capitalize()}")
    assert jvm_project(environment, language).files == (
        "meta.yaml",
        "problem.md",
        "solutions/explanation.md",
        f"solutions/reference/{entry}",
        "starter/README.md",
        "starter/build.gradle.kts",
        "starter/gradle.properties",
        "starter/gradle/wrapper/gradle-wrapper.properties",
        "starter/settings.gradle.kts",
        f"starter/{entry}",
        "tests.json",
    )


@pytest.mark.parametrize("language", [Language.JAVA, Language.KOTLIN])
def test_a_jvm_project_lists_its_language_alone(environment, language):
    meta = environment.problems.load(jvm_project(environment, language).slug).meta
    assert (meta.kind, meta.languages) == (ProblemKind.PROJECT, (language,))


@pytest.mark.parametrize("language", [Language.JAVA, Language.KOTLIN])
def test_a_jvm_project_names_its_entry_class_and_test_package(environment, language):
    meta = environment.problems.load(jvm_project(environment, language).slug).meta
    assert meta.project is not None
    assert (meta.project.entry, meta.project.tests) == (
        f"app.BankProject{language.capitalize()}",
        f"src/test/{language}/app",
    )


@pytest.mark.parametrize("language", [Language.JAVA, Language.KOTLIN])
def test_a_jvm_projects_build_files_are_the_templates(environment, language):
    """Check S15 holds the starter to these exact files."""
    created = jvm_project(environment, language)
    starter = environment.root / created.directory / "starter"
    expected = jvm_build_files(created.slug, language)
    assert {path: (starter / path).read_text() for path in expected} == expected


@pytest.mark.parametrize("language", [Language.JAVA, Language.KOTLIN])
def test_a_jvm_projects_starter_declares_level_ones_method_only(environment, language):
    created = jvm_project(environment, language)
    class_name = f"BankProject{language.capitalize()}"
    entry = environment.root / created.directory / "starter" / jvm_entry(language, class_name)
    text = entry.read_text()
    assert (f"class {class_name}" in text, " put(" in text, " get(" in text) == (True, True, False)


@pytest.mark.parametrize("language", [Language.JAVA, Language.KOTLIN])
def test_a_jvm_projects_overlay_implements_every_level(environment, language):
    created = jvm_project(environment, language)
    class_name = f"BankProject{language.capitalize()}"
    reference = environment.root / created.directory / "solutions" / "reference"
    text = (reference / jvm_entry(language, class_name)).read_text()
    assert (" put(" in text, " get(" in text) == (True, True)


RUST_PROJECT_FILES = (
    "meta.yaml",
    "problem.md",
    "solutions/explanation.md",
    "solutions/reference/src/lib.rs",
    "starter/.cargo/config.toml",
    "starter/Cargo.toml",
    "starter/README.md",
    "starter/src/lib.rs",
    "tests.json",
)


def test_a_rust_project_gets_its_starter_and_overlay_and_no_reference_file(environment):
    created = create(environment, "bank-project-rust", TemplateName.PROJECT_RUST)
    assert created.files == RUST_PROJECT_FILES


def test_a_rust_project_lists_rust_alone_with_the_crate_as_entry(environment):
    created = create(environment, "bank-project-rust", TemplateName.PROJECT_RUST)
    meta = environment.problems.load(created.slug).meta
    assert (meta.languages, meta.project and meta.project.entry) == (
        (Language.RUST,),
        "bank_project_rust",
    )


def test_a_rust_projects_crate_is_named_after_the_entry(environment):
    created = create(environment, "bank-project-rust", TemplateName.PROJECT_RUST)
    manifest = (environment.root / created.directory / "starter" / "Cargo.toml").read_text()
    assert 'name = "bank_project_rust"\n' in manifest


def test_a_rust_projects_starter_declares_level_ones_method_only(environment):
    created = create(environment, "bank-project-rust", TemplateName.PROJECT_RUST)
    entry = (environment.root / created.directory / "starter" / "src" / "lib.rs").read_text()
    assert (
        "pub struct BankProjectRust {" in entry,
        "    pub fn put(" in entry,
        "    pub fn get(" in entry,
    ) == (True, True, False)


def test_a_rust_projects_overlay_implements_every_level(environment):
    created = create(environment, "bank-project-rust", TemplateName.PROJECT_RUST)
    overlay = environment.root / created.directory / "solutions" / "reference" / "src" / "lib.rs"
    text = overlay.read_text()
    assert ("    pub fn put(" in text, "    pub fn get(" in text) == (True, True)


# a Go project on the virtual clock

CLOCK_SLUG = "waiter-project-go"


def create_clock(environment, slug: str = CLOCK_SLUG):
    request = ScaffoldRequest(slug, TemplateName.PROJECT_GO, virtual_clock=True)
    return create_problem(environment, TEMPLATES, request)


def clock_file(environment, created, path: str) -> str:
    return (environment.root / created.directory / path).read_text()


def test_a_go_clock_project_gets_its_starter_and_overlay_and_no_reference_file(environment):
    created = create_clock(environment)
    assert created.files == (
        "meta.yaml",
        "problem.md",
        "solutions/explanation.md",
        "solutions/reference/app.go",
        "starter/README.md",
        "starter/app.go",
        "starter/go.mod",
        "tests.json",
    )


def test_a_go_clock_project_reports_that_it_is_on_the_virtual_clock(environment):
    created = create_clock(environment)
    assert (created.template, created.virtual_clock) == (TemplateName.PROJECT_GO, True)


def test_a_go_project_without_the_flag_is_on_the_real_clock(environment):
    created = create(environment, "bank-project-go", TemplateName.PROJECT_GO)
    assert (created.virtual_clock, "clock" in clock_file(environment, created, "meta.yaml")) == (
        False,
        False,
    )


def test_a_go_clock_project_declares_the_virtual_clock_in_go(environment):
    meta = environment.problems.load(create_clock(environment).slug).meta
    assert (meta.languages, meta.project.clock) == ((Language.GO,), ProjectClock.VIRTUAL)  # type: ignore[union-attr]


def test_a_go_clock_projects_level_2_method_waits(environment):
    create_clock(environment)
    signature = environment.problems.load(CLOCK_SLUG).meta.signature
    assert isinstance(signature, ClassSignature)
    assert [(method.name, method.level) for method in signature.methods] == [
        ("put", 1),
        ("waitFor", 2),
    ]


def test_a_go_clock_projects_hang_guard_is_a_few_seconds(environment):
    create_clock(environment)
    assert environment.problems.load(CLOCK_SLUG).meta.hang_guard_ms == 3_000


def test_a_go_clock_projects_example_spawns_advances_joins_and_reads_the_clock(environment):
    create_clock(environment)
    cases = {case.id: case for case in environment.problems.load(CLOCK_SLUG).cases}
    sequence = cases["ex2"].input
    assert isinstance(sequence, OperationSequence)
    assert sequence.ops == (
        "WaiterProjectGo",
        "@spawn",
        "@advance",
        "put",
        "@join",
        "@now",
        "waitFor",
        "@now",
    )


def test_a_go_clock_projects_starter_says_go_1_25(environment):
    created = create_clock(environment)
    assert "\ngo 1.25\n" in clock_file(environment, created, "starter/go.mod")


def test_a_go_clock_projects_module_is_its_slug(environment):
    created = create_clock(environment)
    assert clock_file(environment, created, "starter/go.mod").startswith(f"module {CLOCK_SLUG}\n")


def test_a_go_clock_projects_starter_declares_level_ones_method_only(environment):
    created = create_clock(environment)
    text = clock_file(environment, created, "starter/app.go")
    assert ("func (a *WaiterProjectGo) Put(" in text, "WaitFor" in text) == (True, False)


def test_a_go_clock_projects_overlay_implements_every_level(environment):
    created = create_clock(environment)
    text = clock_file(environment, created, "solutions/reference/app.go")
    assert (
        "func (a *WaiterProjectGo) Put(" in text,
        "func (a *WaiterProjectGo) WaitFor(" in text,
    ) == (
        True,
        True,
    )


def test_a_go_clock_projects_readme_teaches_testing_on_the_clock(environment):
    created = create_clock(environment)
    readme = clock_file(environment, created, "starter/README.md")
    assert "## Testing on the virtual clock" in readme
    assert "synctest.Test(t, func(t *testing.T) {" in readme


def test_a_go_clock_project_passes_static_checks_after_replacing_the_placeholders(environment):
    created = create_clock(environment)
    replace_placeholders(environment.root / created.directory)
    assert static_errors(environment, CLOCK_SLUG) == ()


def test_a_go_clock_project_fails_static_checks_until_the_placeholders_are_replaced(environment):
    create_clock(environment)
    assert any("TODO" in error for error in static_errors(environment, CLOCK_SLUG))


def test_a_go_clock_project_with_a_real_clock_go_mod_fails_static_checks(environment):
    created = create_clock(environment)
    replace_placeholders(environment.root / created.directory)
    go_mod = environment.root / created.directory / "starter" / "go.mod"
    go_mod.write_text(go_mod.read_text().replace("go 1.25", "go 1.24"))
    assert static_errors(environment, CLOCK_SLUG) == (
        f'problems/0003-{CLOCK_SLUG}/starter/go.mod: says "go 1.24"; '
        "a virtual-clock project's go.mod says go 1.25",
    )


def test_the_virtual_clock_flag_on_another_template_writes_nothing(environment):
    request = ScaffoldRequest("max-gap", TemplateName.ARRAY, virtual_clock=True)
    with pytest.raises(UsageError, match="applies to the project-"):
        create_problem(environment, TEMPLATES, request)
    assert not environment.workspace.exists("problems/0003-max-gap")


def test_the_virtual_clock_flag_on_a_language_without_a_graded_clock_writes_nothing(
    environment, monkeypatch
):
    monkeypatch.setattr(scaffold, "GRADED_CLOCK_LANGUAGES", frozenset[Language]())
    request = ScaffoldRequest("waiter-project-rust", TemplateName.PROJECT_RUST, virtual_clock=True)
    with pytest.raises(UsageError, match="does not grade the virtual clock"):
        create_problem(environment, TEMPLATES, request)
    assert not environment.workspace.exists("problems/0003-waiter-project-rust")


# a Python project on the virtual clock

PYTHON_CLOCK_SLUG = "waiter-project-python"


def create_python_clock(environment):
    request = ScaffoldRequest(PYTHON_CLOCK_SLUG, TemplateName.PROJECT_PYTHON, virtual_clock=True)
    return create_problem(environment, TEMPLATES, request)


def test_a_python_clock_project_gets_its_starter_and_overlay(environment):
    assert create_python_clock(environment).files == (
        "meta.yaml",
        "problem.md",
        "solutions/explanation.md",
        "solutions/reference/app/main.py",
        "starter/README.md",
        "starter/app/main.py",
        "starter/pyproject.toml",
        "tests.json",
    )


def test_a_python_clock_projects_level_2_method_is_async(environment):
    create_python_clock(environment)
    signature = environment.problems.load(PYTHON_CLOCK_SLUG).meta.signature
    assert isinstance(signature, ClassSignature)
    assert [(method.name, method.is_async) for method in signature.methods] == [
        ("put", False),
        ("waitFor", True),
    ]


def test_a_python_clock_projects_overlay_awaits_in_its_waiting_method(environment):
    created = create_python_clock(environment)
    text = clock_file(environment, created, "solutions/reference/app/main.py")
    assert "    async def wait_for(self, key: str, wait_ms: int) -> str:\n" in text


def test_a_python_clock_projects_starter_declares_level_ones_method_only(environment):
    created = create_python_clock(environment)
    text = clock_file(environment, created, "starter/app/main.py")
    assert ("    def put(self, key: str, value: str) -> str:\n" in text, "wait_for" in text) == (
        True,
        False,
    )


def test_a_python_clock_projects_readme_teaches_testing_on_the_clock(environment):
    created = create_python_clock(environment)
    readme = clock_file(environment, created, "starter/README.md")
    assert "## Testing on the virtual clock" in readme
    assert "from cs_support.virtual_clock import advance, now, settle" in readme


def test_a_python_clock_project_passes_static_checks_after_replacing_the_placeholders(
    environment,
):
    created = create_python_clock(environment)
    replace_placeholders(environment.root / created.directory)
    assert static_errors(environment, PYTHON_CLOCK_SLUG) == ()


def test_a_python_clock_starter_without_the_plugin_fails_static_checks(environment):
    created = create_python_clock(environment)
    replace_placeholders(environment.root / created.directory)
    pyproject = environment.root / created.directory / "starter" / "pyproject.toml"
    pyproject.write_text(pyproject.read_text().replace(" -p cs_support.virtual_clock", ""))
    assert static_errors(environment, PYTHON_CLOCK_SLUG) == (
        f"problems/0003-{PYTHON_CLOCK_SLUG}/starter/pyproject.toml: loads no "
        "cs_support.virtual_clock; a virtual-clock project's addopts holds "
        "-p cs_support.virtual_clock",
    )


# a TypeScript project on the virtual clock

TYPESCRIPT_CLOCK_SLUG = "waiter-project-typescript"


def create_typescript_clock(environment):
    request = ScaffoldRequest(
        TYPESCRIPT_CLOCK_SLUG, TemplateName.PROJECT_TYPESCRIPT, virtual_clock=True
    )
    return create_problem(environment, TEMPLATES, request)


def test_a_typescript_clock_project_gets_the_clock_helper_in_its_starter(environment):
    assert "starter/tests/virtual-clock.ts" in create_typescript_clock(environment).files


def test_a_typescript_clock_projects_level_2_method_returns_a_promise(environment):
    created = create_typescript_clock(environment)
    text = clock_file(environment, created, "solutions/reference/src/main.ts")
    assert "  async waitFor(key: string, waitMs: number): Promise<string> {\n" in text


def test_a_typescript_clock_projects_readme_teaches_testing_on_the_clock(environment):
    created = create_typescript_clock(environment)
    readme = clock_file(environment, created, "starter/README.md")
    assert "## Testing on the virtual clock" in readme
    assert 'import { virtualClock } from "./virtual-clock.ts";' in readme


def test_a_typescript_clock_project_passes_static_checks_after_replacing_the_placeholders(
    environment,
):
    created = create_typescript_clock(environment)
    replace_placeholders(environment.root / created.directory)
    assert static_errors(environment, TYPESCRIPT_CLOCK_SLUG) == ()


def test_a_typescript_clock_starter_with_an_edited_helper_fails_static_checks(environment):
    created = create_typescript_clock(environment)
    replace_placeholders(environment.root / created.directory)
    helper = environment.root / created.directory / "starter" / "tests" / "virtual-clock.ts"
    helper.write_text(helper.read_text() + "// mine\n")
    assert static_errors(environment, TYPESCRIPT_CLOCK_SLUG) == (
        f"problems/0003-{TYPESCRIPT_CLOCK_SLUG}/starter/tests/virtual-clock.ts: is not the clock "
        "helper that the template writes; copy runners/typescript/lib/virtual-clock.ts again",
    )


# a Kotlin project on the virtual clock

KOTLIN_CLOCK_SLUG = "waiter-project-kotlin"


def create_kotlin_clock(environment):
    request = ScaffoldRequest(KOTLIN_CLOCK_SLUG, TemplateName.PROJECT_KOTLIN, virtual_clock=True)
    return create_problem(environment, TEMPLATES, request)


def test_a_kotlin_clock_projects_build_applies_the_coroutines_plugin(environment):
    created = create_kotlin_clock(environment)
    expected = jvm_build_files(created.slug, Language.KOTLIN, virtual_clock=True)
    for path, text in expected.items():
        assert clock_file(environment, created, f"starter/{path}") == text


def test_a_kotlin_clock_projects_level_2_method_is_a_suspend_function(environment):
    created = create_kotlin_clock(environment)
    reference = f"solutions/reference/{jvm_entry(Language.KOTLIN, 'WaiterProjectKotlin')}"
    text = clock_file(environment, created, reference)
    assert "    suspend fun waitFor(key: String, waitMs: Long): String {\n" in text


def test_a_kotlin_clock_projects_readme_teaches_testing_on_the_clock(environment):
    created = create_kotlin_clock(environment)
    readme = clock_file(environment, created, "starter/README.md")
    assert "## Testing on the virtual clock" in readme
    assert "import kotlinx.coroutines.test.runTest" in readme


def test_a_kotlin_clock_project_passes_static_checks_after_replacing_the_placeholders(
    environment,
):
    created = create_kotlin_clock(environment)
    replace_placeholders(environment.root / created.directory)
    assert static_errors(environment, KOTLIN_CLOCK_SLUG) == ()


def test_a_kotlin_clock_starter_without_the_coroutines_plugin_fails_static_checks(environment):
    created = create_kotlin_clock(environment)
    replace_placeholders(environment.root / created.directory)
    build = environment.root / created.directory / "starter" / "build.gradle.kts"
    build.write_text(jvm_build_files(created.slug, Language.KOTLIN)["build.gradle.kts"])
    assert static_errors(environment, KOTLIN_CLOCK_SLUG) == (
        f"problems/0003-{KOTLIN_CLOCK_SLUG}/starter/build.gradle.kts: differs from what "
        "cstudy new --from-template project-kotlin --virtual-clock writes",
    )


# a Rust project on the virtual clock

RUST_CLOCK_SLUG = "waiter-project-rust"


def create_rust_clock(environment):
    request = ScaffoldRequest(RUST_CLOCK_SLUG, TemplateName.PROJECT_RUST, virtual_clock=True)
    return create_problem(environment, TEMPLATES, request)


def test_a_rust_clock_projects_level_2_method_is_an_async_fn(environment):
    created = create_rust_clock(environment)
    text = clock_file(environment, created, "solutions/reference/src/lib.rs")
    assert "    pub async fn wait_for(&self, key: String, wait_ms: i64) -> String {\n" in text


def test_a_rust_clock_projects_starter_depends_on_tokio(environment):
    created = create_rust_clock(environment)
    manifest = clock_file(environment, created, "starter/Cargo.toml")
    assert f"[dependencies]\ntokio = {RUST_CLOCK_CRATES['tokio']}\n" in manifest


def test_a_rust_clock_projects_readme_teaches_testing_on_the_clock(environment):
    created = create_rust_clock(environment)
    readme = clock_file(environment, created, "starter/README.md")
    assert "## Testing on the virtual clock" in readme
    assert "#[tokio::test(start_paused = true)]" in readme


def test_a_rust_clock_project_passes_static_checks_after_replacing_the_placeholders(environment):
    created = create_rust_clock(environment)
    replace_placeholders(environment.root / created.directory)
    assert static_errors(environment, RUST_CLOCK_SLUG) == ()


def test_a_rust_clock_starter_without_tokio_fails_static_checks(environment):
    created = create_rust_clock(environment)
    replace_placeholders(environment.root / created.directory)
    manifest = environment.root / created.directory / "starter" / "Cargo.toml"
    manifest.write_text(manifest.read_text().partition("[dependencies]")[0])
    assert static_errors(environment, RUST_CLOCK_SLUG) == (
        f"problems/0003-{RUST_CLOCK_SLUG}/starter/Cargo.toml: a virtual-clock project's "
        f"[dependencies] needs tokio = {RUST_CLOCK_CRATES['tokio']}",
    )


# a project with stress cases

STRESS_SLUG = "tally-counter"
STRESS_CLASS = "TallyCounter"
STRESS_ENTRIES = {
    Language.PYTHON: "app/main.py",
    Language.TYPESCRIPT: "src/main.ts",
    Language.JAVA: f"src/main/java/app/{STRESS_CLASS}.java",
    Language.KOTLIN: f"src/main/kotlin/app/{STRESS_CLASS}.kt",
    Language.GO: "app.go",
    Language.RUST: "src/lib.rs",
}
STRESS_COMBINATIONS = [
    (template, clock)
    for clock, templates in (
        (
            False,
            (
                TemplateName.PROJECT_PYTHON,
                TemplateName.PROJECT_JAVA,
                TemplateName.PROJECT_KOTLIN,
                TemplateName.PROJECT_GO,
                TemplateName.PROJECT_RUST,
            ),
        ),
        (
            True,
            (
                TemplateName.PROJECT_PYTHON,
                TemplateName.PROJECT_TYPESCRIPT,
                TemplateName.PROJECT_KOTLIN,
                TemplateName.PROJECT_GO,
                TemplateName.PROJECT_RUST,
            ),
        ),
    )
    for template in templates
]
JVM_STRESS_TEMPLATES = (TemplateName.PROJECT_JAVA, TemplateName.PROJECT_KOTLIN)
STRESS_IDS = [f"{template}{'-clock' if clock else ''}" for template, clock in STRESS_COMBINATIONS]


def create_stress(environment, template: TemplateName, clock: bool):
    request = ScaffoldRequest(STRESS_SLUG, template, virtual_clock=clock, stress=True)
    return create_problem(environment, TEMPLATES, request)


def entry_of(template: TemplateName) -> str:
    return STRESS_ENTRIES[scaffold.PROJECT_TEMPLATE_LANGUAGES[template]]


stress_combinations = pytest.mark.parametrize(
    ("template", "clock"), STRESS_COMBINATIONS, ids=STRESS_IDS
)


@stress_combinations
def test_a_stress_project_reports_what_it_was_written_with(environment, template, clock):
    created = create_stress(environment, template, clock)
    assert (created.template, created.virtual_clock, created.stress) == (template, clock, True)


@stress_combinations
def test_a_stress_project_keeps_a_reference_overlay_and_a_broken_one_beside_it(
    environment, template, clock
):
    created = create_stress(environment, template, clock)
    entry = entry_of(template)
    assert {f"solutions/reference/{entry}", f"solutions/broken/lost-update/{entry}"} <= set(
        created.files
    )


@stress_combinations
def test_a_stress_projects_broken_overlay_changes_the_reference(environment, template, clock):
    created = create_stress(environment, template, clock)
    entry = entry_of(template)
    reference = clock_file(environment, created, f"solutions/reference/{entry}")
    broken = clock_file(environment, created, f"solutions/broken/lost-update/{entry}")
    assert broken != reference


@stress_combinations
def test_a_stress_project_declares_the_broken_overlay_and_the_case_that_catches_it(
    environment, template, clock
):
    create_stress(environment, template, clock)
    problem = environment.problems.load(STRESS_SLUG)
    broken = problem.meta.concurrency.broken  # type: ignore[union-attr]
    stress_cases = [case for case in problem.cases if isinstance(case.input, StressScenario)]
    assert [(b.id, b.caught_by) for b in broken] == [("lost-update", ("s1",))]
    assert [(case.id, case.level, case.visible) for case in stress_cases] == [("s1", 2, False)]


@stress_combinations
def test_a_stress_project_keeps_two_sequential_cases_at_each_level_in_view(
    environment, template, clock
):
    create_stress(environment, template, clock)
    cases = environment.problems.load(STRESS_SLUG).cases
    visible = [(case.id, case.level) for case in cases if case.visible]
    assert visible == [("ex1", 1), ("ex2", 2)]


@stress_combinations
def test_a_stress_project_is_on_the_clock_it_was_asked_for(environment, template, clock):
    create_stress(environment, template, clock)
    meta = environment.problems.load(STRESS_SLUG).meta
    declared = meta.project.clock  # type: ignore[union-attr]
    assert declared == (ProjectClock.VIRTUAL if clock else None)


EXPECTED_MODELS = {
    (TemplateName.PROJECT_PYTHON, False): ConcurrencyModel.THREADS,
    (TemplateName.PROJECT_PYTHON, True): ConcurrencyModel.ASYNC,
    (TemplateName.PROJECT_TYPESCRIPT, True): ConcurrencyModel.ASYNC,
    (TemplateName.PROJECT_JAVA, False): ConcurrencyModel.THREADS,
    (TemplateName.PROJECT_KOTLIN, False): ConcurrencyModel.THREADS,
    (TemplateName.PROJECT_KOTLIN, True): ConcurrencyModel.THREADS,
    (TemplateName.PROJECT_GO, False): ConcurrencyModel.THREADS,
    (TemplateName.PROJECT_GO, True): ConcurrencyModel.THREADS,
    (TemplateName.PROJECT_RUST, False): ConcurrencyModel.THREADS,
    (TemplateName.PROJECT_RUST, True): ConcurrencyModel.THREADS,
}


@stress_combinations
def test_a_stress_project_runs_in_the_model_its_language_and_methods_need(
    environment, template, clock
):
    create_stress(environment, template, clock)
    concurrency = environment.problems.load(STRESS_SLUG).meta.concurrency
    language = scaffold.PROJECT_TEMPLATE_LANGUAGES[template]
    assert concurrency.model_for(language) is EXPECTED_MODELS[(template, clock)]  # type: ignore[union-attr]


@pytest.mark.parametrize(
    ("template", "clock"),
    [combination for combination in STRESS_COMBINATIONS if combination[0] in JVM_STRESS_TEMPLATES],
)
def test_a_jvm_stress_project_runs_every_thread_kind(environment, template, clock):
    create_stress(environment, template, clock)
    concurrency = environment.problems.load(STRESS_SLUG).meta.concurrency
    assert concurrency.jvm_threads == (ThreadKind.PLATFORM, ThreadKind.VIRTUAL)  # type: ignore[union-attr]


@stress_combinations
def test_a_stress_project_passes_static_checks_after_replacing_the_placeholders(
    environment, template, clock
):
    created = create_stress(environment, template, clock)
    replace_placeholders(environment.root / created.directory)
    assert static_errors(environment, STRESS_SLUG) == ()


@stress_combinations
def test_a_stress_project_fails_static_checks_until_the_placeholders_are_replaced(
    environment, template, clock
):
    create_stress(environment, template, clock)
    assert any("TODO" in error for error in static_errors(environment, STRESS_SLUG))


@stress_combinations
def test_a_stress_project_writes_the_build_files_of_its_base_template(environment, template, clock):
    """Check S15 compares them with the template's, so the stress overlay must not alter them."""
    created = create_stress(environment, template, clock)
    request = ScaffoldRequest(STRESS_SLUG, template, virtual_clock=clock)
    placeholders = scaffold.plan_scaffold(request, "0003").placeholders()
    base = scaffold.template_directories(request)[0]
    changed = {f"starter/{entry_of(template)}", "starter/README.md"}
    for name, text in TEMPLATES.files(base).items():
        path = render_template(name, placeholders)
        if path.startswith("starter/") and path not in changed:
            assert clock_file(environment, created, path) == render_template(text, placeholders)


def test_a_rust_stress_project_shares_the_instance_through_shared_receivers(environment):
    created = create_stress(environment, TemplateName.PROJECT_RUST, False)
    text = clock_file(environment, created, "solutions/reference/src/lib.rs")
    assert ("&self" in text, "&mut self" in text) == (True, False)


def test_a_rust_stress_projects_readme_says_why_methods_take_a_shared_receiver(environment):
    created = create_stress(environment, TemplateName.PROJECT_RUST, False)
    readme = clock_file(environment, created, "starter/README.md")
    assert "every method takes `&self`" in readme


def test_a_python_stress_projects_reference_locks_what_the_broken_overlay_does_not(environment):
    created = create_stress(environment, TemplateName.PROJECT_PYTHON, False)
    reference = clock_file(environment, created, "solutions/reference/app/main.py")
    broken = clock_file(environment, created, "solutions/broken/lost-update/app/main.py")
    assert (reference.count("with self._lock:"), broken.count("with self._lock:")) == (3, 2)


@pytest.mark.parametrize(
    ("template", "clock", "message"),
    [
        (TemplateName.ARRAY, False, "--stress applies to the project-* templates"),
        (TemplateName.PROJECT_TYPESCRIPT, False, "without --virtual-clock"),
        (TemplateName.PROJECT_JAVA, True, "Java has no virtual clock"),
    ],
)
def test_stress_where_it_does_not_apply_writes_nothing(environment, template, clock, message):
    request = ScaffoldRequest("tally-counter", template, virtual_clock=clock, stress=True)
    with pytest.raises(UsageError, match=re.escape(message)):
        create_problem(environment, TEMPLATES, request)
    assert not environment.workspace.exists("problems/0003-tally-counter")
