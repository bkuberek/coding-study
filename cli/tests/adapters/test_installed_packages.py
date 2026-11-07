"""The installed packages `cstudy about` credits (docs/specs/cli.md#cstudy-about), read from the
metadata of the environment the tests run in, and from files in a temporary folder."""

from importlib import metadata
from pathlib import Path

import pytest

from coding_study.adapters.installed_packages import (
    NOTICE_FILE,
    InstalledSoftware,
    declared_license,
    requirement_name,
)

MIT_CLASSIFIER = "License :: OSI Approved :: MIT License"


@pytest.fixture(scope="module")
def software() -> InstalledSoftware:
    return InstalledSoftware(Path("no-static-directory"))


def test_a_requirement_is_named_without_its_version():
    assert requirement_name("rich>=15.0") == "rich"


def test_a_requirement_is_named_without_its_marker():
    assert requirement_name("colorama; sys_platform == 'win32'") == "colorama"


def test_a_requirement_is_named_without_its_extras():
    assert requirement_name("uvicorn[standard]>=0.54") == "uvicorn"


def test_a_requirement_for_an_extra_is_not_a_dependency():
    assert requirement_name("pytest>=9; extra == 'test'") is None


def test_a_requirement_is_named_in_lower_case_with_hyphens():
    assert requirement_name("Markdown_It.Py>=4") == "markdown-it-py"


def test_the_license_expression_is_the_license():
    assert declared_license("BSD-3-Clause", None, []) == "BSD-3-Clause"


def test_the_expression_outranks_the_other_fields():
    assert declared_license("MIT", "Other", [MIT_CLASSIFIER]) == "MIT"


def test_a_short_license_field_is_the_license():
    assert declared_license(None, "MIT", []) == "MIT"


def test_a_license_field_holding_the_whole_text_is_not_the_license():
    text = "Permission is hereby granted,\nfree of charge"
    assert declared_license(None, text, []) == ""


def test_a_license_field_too_long_for_a_name_is_not_the_license():
    assert declared_license(None, "x" * 61, []) == ""


def test_a_license_classifier_is_the_license_without_its_prefix():
    assert declared_license(None, None, ["Typing :: Typed", MIT_CLASSIFIER]) == "MIT License"


def test_a_package_that_declares_no_license_has_none():
    assert declared_license(None, None, []) == ""


def test_the_python_packages_are_those_cstudy_needs_to_run(software):
    names = [credit.name for credit in software.python_packages()]
    assert {"rich", "starlette", "typer"} <= set(names)


def test_the_python_packages_include_what_they_need_in_turn(software):
    names = [credit.name for credit in software.python_packages()]
    assert "click" in names


def test_cstudy_does_not_credit_itself(software):
    assert "coding-study" not in [credit.name for credit in software.python_packages()]


def test_the_development_tools_are_not_credited(software):
    names = [credit.name for credit in software.python_packages()]
    assert "pytest" not in names


def test_the_python_packages_come_in_name_order(software):
    names = [credit.name for credit in software.python_packages()]
    assert names == sorted(names)


def test_a_python_package_has_the_version_that_is_installed(software):
    rich = next(credit for credit in software.python_packages() if credit.name == "rich")
    assert rich.version == metadata.version("rich")


def test_a_python_package_has_the_license_it_declares(software):
    rich = next(credit for credit in software.python_packages() if credit.name == "rich")
    assert rich.license == "MIT"


def test_a_python_package_license_text_is_the_one_the_package_ships(software):
    assert "Permission is hereby granted" in software.python_license_texts()["rich"]


def test_a_package_that_ships_two_license_files_has_both(software):
    assert software.python_license_texts()["markdown-it-py"].count("Copyright") >= 2


def test_cstudys_own_license_is_the_text_of_the_mit_license(software):
    text = software.own_license_text()
    assert "MIT License" in text
    assert "Permission is hereby granted" in text


def test_the_notice_is_read_from_the_static_directory(tmp_path):
    (tmp_path / NOTICE_FILE).write_text("the notice\n")
    assert InstalledSoftware(tmp_path).web_ui_notice() == "the notice\n"


def test_no_notice_in_the_static_directory_means_none(tmp_path):
    assert InstalledSoftware(tmp_path).web_ui_notice() is None
