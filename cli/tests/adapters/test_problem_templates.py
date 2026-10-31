import pytest

from coding_study.adapters.problem_templates import PackagedProblemTemplates
from coding_study.domain.scaffold import TemplateName
from coding_study.domain.workspace_projects import RUST_CARGO_CONFIG

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


def test_the_typescript_starters_build_files_drop_their_template_suffix():
    files = PackagedProblemTemplates().files(TemplateName.PROJECT_TYPESCRIPT)
    assert '"type": "module"' in files["starter/package.json"]


def test_a_file_that_is_code_only_once_filled_in_drops_its_template_suffix():
    files = PackagedProblemTemplates().files(TemplateName.PROJECT_PYTHON)
    assert "class {{class_name}}:" in files["starter/app/main.py"]


def test_files_hold_the_template_text():
    files = PackagedProblemTemplates().files(TemplateName.ARRAY)
    assert files["problem.md"].startswith("# {{title}}\n")
