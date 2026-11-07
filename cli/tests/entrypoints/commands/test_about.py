"""`cstudy about` (docs/specs/cli.md#cstudy-about): the version, the license, the links and the
credits. It needs no workspace and reads no configuration."""

from importlib import metadata

import pytest
from typer.testing import CliRunner

from coding_study.domain.about import SPONSOR_LINKS, WEBSITE
from coding_study.entrypoints import cli
from coding_study.entrypoints.shared import ExitCode

runner = CliRunner()


def about(*arguments: str):
    return runner.invoke(cli.app, ["about", *arguments], env={"NO_COLOR": "1"})


def test_about_exits_with_success():
    assert about().exit_code == ExitCode.SUCCESS


def test_about_names_the_installed_version():
    assert f"cstudy {metadata.version('coding-study')}" in about().stdout


def test_about_names_the_license():
    assert "MIT" in about().stdout


def test_about_links_to_the_website():
    assert WEBSITE in about().stdout


@pytest.mark.parametrize("link", SPONSOR_LINKS, ids=lambda link: link.label)
def test_about_links_to_each_sponsor_target(link):
    assert link.url in about().stdout


def test_about_says_how_to_read_the_credits_and_the_licenses():
    output = about().stdout
    assert "cstudy about --credits" in output
    assert "cstudy about --licenses" in output


def test_about_needs_no_workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert about().exit_code == ExitCode.SUCCESS


def test_about_lists_no_credits_unasked():
    assert "Python packages" not in about().stdout


def test_credits_list_the_python_packages_with_versions_and_licenses():
    output = about("--credits").stdout
    assert f"rich {metadata.version('rich')} MIT" in " ".join(output.split())


def test_credits_name_the_language_servers():
    assert "basedpyright" in about("--credits").stdout


def test_credits_name_the_packages_of_the_web_page():
    assert "@codemirror/view" in about("--credits").stdout


def test_credits_leave_the_summary_out():
    assert WEBSITE not in about("--credits").stdout


def test_licenses_print_the_full_text_of_cstudys_own_license():
    assert "Permission is hereby granted" in about("--licenses").stdout


def test_licenses_print_the_text_of_a_package_cstudy_uses():
    assert f"rich {metadata.version('rich')}" in about("--licenses").stdout


def test_credits_and_licenses_together_are_refused():
    result = about("--credits", "--licenses")
    assert result.exit_code == ExitCode.USAGE_ERROR


def test_credits_and_licenses_together_say_to_choose_one():
    assert "choose one" in about("--credits", "--licenses").output


def test_about_is_listed_among_the_commands():
    assert "about" in runner.invoke(cli.app, ["--help"]).stdout
