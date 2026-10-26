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


@pytest.mark.parametrize("template", [name for name in TemplateName if name != "concurrent"])
def test_every_template_has_the_scaffold_files(template):
    assert set(PackagedProblemTemplates().files(template)) == TEMPLATE_FILES


def test_the_concurrent_template_has_no_generator():
    files = set(PackagedProblemTemplates().files(TemplateName.CONCURRENT))
    assert files == TEMPLATE_FILES - {"generator.py"}


def test_files_hold_the_template_text():
    files = PackagedProblemTemplates().files(TemplateName.ARRAY)
    assert files["problem.md"].startswith("# {{title}}\n")
