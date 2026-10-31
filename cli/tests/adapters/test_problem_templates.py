import pytest

from coding_study.adapters.problem_templates import PackagedProblemTemplates
from coding_study.domain.scaffold import TemplateName

TEMPLATE_FILES = {
    "generator.py",
    "meta.yaml",
    "problem.md",
    "solutions/explanation.md",
    "tests.json",
}


@pytest.mark.parametrize(
    "template", [name for name in TemplateName if name not in ("concurrent", "project-python")]
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


def test_a_file_that_is_code_only_once_filled_in_drops_its_template_suffix():
    files = PackagedProblemTemplates().files(TemplateName.PROJECT_PYTHON)
    assert "class {{class_name}}:" in files["starter/app/main.py"]


def test_files_hold_the_template_text():
    files = PackagedProblemTemplates().files(TemplateName.ARRAY)
    assert files["problem.md"].startswith("# {{title}}\n")
