import tomllib

import pytest

from coding_study.adapters.problem_templates import PackagedProblemTemplates
from coding_study.domain.problem import Language
from coding_study.domain.project import RUST_CLOCK_CRATES
from coding_study.domain.project_checks import jvm_build_files
from coding_study.domain.scaffold import TemplateName
from coding_study.domain.workspace_projects import RUST_CARGO_CONFIG
from tests.helpers import REPOSITORY_ROOT

TEMPLATE_FILES = {
    "generator.py",
    "meta.yaml",
    "problem.md",
    "solutions/explanation.md",
    "tests.json",
}


@pytest.mark.parametrize(
    "template",
    [
        name
        for name in TemplateName
        if name
        not in (
            "concurrent",
            "project-python",
            "project-typescript",
            "project-java",
            "project-kotlin",
            "project-go",
            "project-rust",
            "project-typescript-service",
            "project-python-service",
            "project-java-service",
            "project-kotlin-service",
        )
    ],
)
def test_every_template_has_the_scaffold_files(template):
    assert set(PackagedProblemTemplates().files(template)) == TEMPLATE_FILES


def test_the_concurrent_template_has_no_generator():
    files = set(PackagedProblemTemplates().files(TemplateName.CONCURRENT))
    assert files == TEMPLATE_FILES - {"generator.py"}


def test_the_python_project_template_has_a_starter_and_an_overlay_instead_of_a_generator():
    files = set(PackagedProblemTemplates().files(TemplateName.PROJECT_PYTHON))
    assert files == TEMPLATE_FILES - {"generator.py"} | {
        "starter/README.md",
        "starter/pyproject.toml",
        "starter/app/main.py",
        "solutions/reference/app/main.py",
    }


def test_the_typescript_project_template_has_a_starter_and_an_overlay_instead_of_a_generator():
    files = set(PackagedProblemTemplates().files(TemplateName.PROJECT_TYPESCRIPT))
    assert files == TEMPLATE_FILES - {"generator.py"} | {
        "starter/README.md",
        "starter/package.json",
        "starter/tsconfig.json",
        "starter/src/main.ts",
        "solutions/reference/src/main.ts",
    }


def test_the_go_project_template_has_a_starter_and_an_overlay_instead_of_a_generator():
    files = set(PackagedProblemTemplates().files(TemplateName.PROJECT_GO))
    assert files == TEMPLATE_FILES - {"generator.py"} | {
        "starter/README.md",
        "starter/go.mod",
        "starter/app.go",
        "solutions/reference/app.go",
    }


def test_the_go_virtual_clock_template_has_the_files_of_the_go_project_template():
    clock = set(PackagedProblemTemplates().files("project-go-clock"))
    assert clock == set(PackagedProblemTemplates().files(TemplateName.PROJECT_GO))


def test_the_go_virtual_clock_starter_says_go_1_25():
    files = PackagedProblemTemplates().files("project-go-clock")
    assert files["starter/go.mod"].startswith("module {{slug}}\n\ngo 1.25\n")


def test_the_go_virtual_clock_template_declares_the_clock():
    meta = PackagedProblemTemplates().files("project-go-clock")["meta.yaml"]
    assert "  clock: virtual\n" in meta


def test_the_python_virtual_clock_template_has_the_files_of_the_python_project_template():
    clock = set(PackagedProblemTemplates().files("project-python-clock"))
    assert clock == set(PackagedProblemTemplates().files(TemplateName.PROJECT_PYTHON))


def test_the_python_virtual_clock_starter_loads_the_clock_plugin():
    files = PackagedProblemTemplates().files("project-python-clock")
    assert "-p cs_support.virtual_clock" in files["starter/pyproject.toml"]


def test_the_python_virtual_clock_template_declares_the_clock_and_an_async_method():
    meta = PackagedProblemTemplates().files("project-python-clock")["meta.yaml"]
    assert ("  clock: virtual\n" in meta, "async: true" in meta) == (True, True)


CLOCK_HELPER = REPOSITORY_ROOT / "runners" / "typescript" / "lib" / "virtual-clock.ts"


def test_the_typescript_virtual_clock_template_adds_the_clock_helper_to_the_project_template():
    clock = set(PackagedProblemTemplates().files("project-typescript-clock"))
    plain = set(PackagedProblemTemplates().files(TemplateName.PROJECT_TYPESCRIPT))
    assert clock == plain | {"starter/tests/virtual-clock.ts"}


def test_the_typescript_virtual_clock_helper_is_the_runners_file_byte_for_byte():
    files = PackagedProblemTemplates().files("project-typescript-clock")
    assert files["starter/tests/virtual-clock.ts"] == CLOCK_HELPER.read_text()


def test_every_typescript_clock_fixture_holds_the_runners_helper():
    fixtures = sorted(
        (REPOSITORY_ROOT / "runners" / "conformance").glob("*/starter/tests/virtual-clock.ts")
    )
    assert fixtures
    assert all(fixture.read_text() == CLOCK_HELPER.read_text() for fixture in fixtures)


def test_the_typescript_virtual_clock_template_declares_the_clock_and_an_async_method():
    meta = PackagedProblemTemplates().files("project-typescript-clock")["meta.yaml"]
    assert ("  clock: virtual\n" in meta, "async: true" in meta) == (True, True)


def test_the_go_starters_module_is_named_after_the_slug():
    files = PackagedProblemTemplates().files(TemplateName.PROJECT_GO)
    assert files["starter/go.mod"].startswith("module {{slug}}\n")


@pytest.mark.parametrize(
    ("template", "language", "extension"),
    [(TemplateName.PROJECT_JAVA, "java", "java"), (TemplateName.PROJECT_KOTLIN, "kotlin", "kt")],
)
def test_a_jvm_project_template_has_a_gradle_starter_and_an_overlay(template, language, extension):
    entry = f"src/main/{language}/app/{{{{class_name}}}}.{extension}"
    files = set(PackagedProblemTemplates().files(template))
    assert files == TEMPLATE_FILES - {"generator.py"} | {
        "starter/README.md",
        "starter/settings.gradle.kts",
        "starter/build.gradle.kts",
        "starter/gradle.properties",
        "starter/gradle/wrapper/gradle-wrapper.properties",
        f"starter/{entry}",
        f"solutions/reference/{entry}",
    }


def test_the_rust_project_template_has_a_starter_and_an_overlay_instead_of_a_generator():
    files = set(PackagedProblemTemplates().files(TemplateName.PROJECT_RUST))
    assert files == TEMPLATE_FILES - {"generator.py"} | {
        "starter/README.md",
        "starter/Cargo.toml",
        "starter/.cargo/config.toml",
        "starter/src/lib.rs",
        "solutions/reference/src/lib.rs",
    }


def test_the_rust_starters_cargo_config_is_the_vendored_source():
    files = PackagedProblemTemplates().files(TemplateName.PROJECT_RUST)
    assert files["starter/.cargo/config.toml"] == RUST_CARGO_CONFIG


def test_the_rust_virtual_clock_template_has_the_files_of_the_rust_project_template():
    clock = set(PackagedProblemTemplates().files("project-rust-clock"))
    assert clock == set(PackagedProblemTemplates().files(TemplateName.PROJECT_RUST))


def test_the_rust_virtual_clock_starter_depends_on_tokio_as_the_runner_declares_it():
    files = PackagedProblemTemplates().files("project-rust-clock")
    manifest = tomllib.loads(files["starter/Cargo.toml"].replace("{{crate_name}}", "waiter"))
    declared = tomllib.loads(f"value = {RUST_CLOCK_CRATES['tokio']}")["value"]
    assert manifest["dependencies"] == {"tokio": declared}


def test_the_rust_virtual_clock_template_declares_the_clock_and_an_async_method():
    meta = PackagedProblemTemplates().files("project-rust-clock")["meta.yaml"]
    assert ("  clock: virtual\n" in meta, "async: true" in meta) == (True, True)


def test_the_typescript_starters_build_files_drop_their_template_suffix():
    files = PackagedProblemTemplates().files(TemplateName.PROJECT_TYPESCRIPT)
    assert '"type": "module"' in files["starter/package.json"]


def test_a_file_that_is_code_only_once_filled_in_drops_its_template_suffix():
    files = PackagedProblemTemplates().files(TemplateName.PROJECT_PYTHON)
    assert "class {{class_name}}:" in files["starter/app/main.py"]


def test_files_hold_the_template_text():
    files = PackagedProblemTemplates().files(TemplateName.ARRAY)
    assert files["problem.md"].startswith("# {{title}}\n")


def test_the_kotlin_virtual_clock_template_has_the_files_of_the_kotlin_project_template():
    clock = set(PackagedProblemTemplates().files("project-kotlin-clock"))
    assert clock == set(PackagedProblemTemplates().files(TemplateName.PROJECT_KOTLIN))


def test_the_kotlin_virtual_clock_starter_builds_on_the_virtual_clock():
    build = PackagedProblemTemplates().files("project-kotlin-clock")["starter/build.gradle.kts"]
    assert build == jvm_build_files("any", Language.KOTLIN, virtual_clock=True)["build.gradle.kts"]


def test_the_kotlin_virtual_clock_template_declares_the_clock_and_a_suspend_method():
    meta = PackagedProblemTemplates().files("project-kotlin-clock")["meta.yaml"]
    assert ("  clock: virtual\n" in meta, "async: true" in meta) == (True, True)


# stress overlays

STRESS_ENTRIES = {
    "project-python": "app/main.py",
    "project-typescript": "src/main.ts",
    "project-java": "src/main/java/app/{{class_name}}.java",
    "project-kotlin": "src/main/kotlin/app/{{class_name}}.kt",
    "project-go": "app.go",
    "project-rust": "src/lib.rs",
}
STRESS_OVERLAYS = [
    f"{template}{variant}-stress"
    for template in STRESS_ENTRIES
    for variant in ("", "-clock")
    if (template, variant) != ("project-java", "-clock")
    if (template, variant) != ("project-typescript", "")
]
S15_COMPARED_FILES = {
    "starter/pyproject.toml",
    "starter/package.json",
    "starter/tsconfig.json",
    "starter/go.mod",
    "starter/Cargo.toml",
    "starter/.cargo/config.toml",
    "starter/settings.gradle.kts",
    "starter/build.gradle.kts",
    "starter/gradle.properties",
    "starter/gradle/wrapper/gradle-wrapper.properties",
    "starter/tests/virtual-clock.ts",
}
"""The starter files that check S15 compares byte for byte with the template's, or whose content it
inspects (docs/specs/authoring.md#what-cstudy-verify-checks)."""


def overlay_entry(overlay: str) -> str:
    return STRESS_ENTRIES[overlay.removesuffix("-stress").removesuffix("-clock")]


@pytest.mark.parametrize("overlay", STRESS_OVERLAYS)
def test_a_stress_overlay_holds_what_a_stress_problem_changes(overlay):
    entry = overlay_entry(overlay)
    files = set(PackagedProblemTemplates().files(overlay))
    expected = TEMPLATE_FILES - {"generator.py"} | {
        f"starter/{entry}",
        f"solutions/reference/{entry}",
        f"solutions/broken/lost-update/{entry}",
    }
    assert files - {"starter/README.md"} == expected


@pytest.mark.parametrize("overlay", STRESS_OVERLAYS)
def test_a_stress_overlay_repeats_no_file_that_check_s15_compares(overlay):
    assert not set(PackagedProblemTemplates().files(overlay)) & S15_COMPARED_FILES


@pytest.mark.parametrize("overlay", STRESS_OVERLAYS)
def test_a_stress_overlay_replaces_files_of_the_template_underneath(overlay):
    base = overlay.removesuffix("-stress")
    files = set(PackagedProblemTemplates().files(overlay))
    layered = set(PackagedProblemTemplates().files(base))
    assert {"meta.yaml", "problem.md", "tests.json"} <= files & layered


@pytest.mark.parametrize("overlay", STRESS_OVERLAYS)
def test_a_stress_overlay_declares_the_stress_case_and_its_broken_overlay(overlay):
    files = PackagedProblemTemplates().files(overlay)
    assert "  broken:\n    - {id: lost-update," in files["meta.yaml"]
    assert '"stress"' in files["tests.json"]
    assert "## Broken: lost-update (" in files["solutions/explanation.md"]


@pytest.mark.parametrize("overlay", [name for name in STRESS_OVERLAYS if "-clock-" in name])
def test_a_clock_stress_overlay_keeps_the_clock_declaration(overlay):
    meta = PackagedProblemTemplates().files(overlay)["meta.yaml"]
    assert "  clock: virtual\n" in meta
    assert "limits: {hang_guard_ms: 3000}\n" in meta


@pytest.mark.parametrize("overlay", [name for name in STRESS_OVERLAYS if "-clock-" not in name])
def test_a_stress_overlay_on_the_real_clock_declares_no_clock(overlay):
    meta = PackagedProblemTemplates().files(overlay)["meta.yaml"]
    assert "clock" not in meta


@pytest.mark.parametrize(
    ("template", "lock"),
    [
        (TemplateName.PROJECT_TYPESCRIPT_SERVICE, "starter/pnpm-lock.yaml"),
        (TemplateName.PROJECT_PYTHON_SERVICE, "starter/uv.lock"),
        (TemplateName.PROJECT_JAVA_SERVICE, "starter/gradle/verification-metadata.xml"),
        (TemplateName.PROJECT_KOTLIN_SERVICE, "starter/gradle/verification-metadata.xml"),
    ],
)
def test_a_service_template_ships_its_lock_and_no_env_file(template, lock):
    files = PackagedProblemTemplates().files(template)

    assert lock in files
    assert "starter/.env" not in files


JVM_SERVICE_TEMPLATES = (TemplateName.PROJECT_JAVA_SERVICE, TemplateName.PROJECT_KOTLIN_SERVICE)


@pytest.mark.parametrize("template", JVM_SERVICE_TEMPLATES)
def test_a_jvm_service_template_builds_offline_outside_install(template):
    meta = PackagedProblemTemplates().files(template)["meta.yaml"]

    assert "install: [gradle, --quiet, resolveDependencies]\n" in meta
    assert "test: [gradle, --offline, test, --rerun]\n" in meta
    assert "install_cache: true" in meta


@pytest.mark.parametrize("template", JVM_SERVICE_TEMPLATES)
def test_a_jvm_service_templates_run_script_builds_offline_then_runs_the_app_in_its_place(
    template,
):
    script = PackagedProblemTemplates().files(template)["starter/scripts/run.sh"]

    assert "gradle --offline --quiet installDist\n" in script
    assert script.endswith("exec build/install/app/bin/app\n")
