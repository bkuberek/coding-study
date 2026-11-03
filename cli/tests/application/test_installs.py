"""What `cstudy doctor` says about the `cstudy` installs on PATH
(docs/specs/cli.md#cstudy-doctor): the `installs` row and the reinstall hint."""

from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.application.installs import (
    Install,
    InstallKind,
    InstallRoots,
    InstallScan,
    classify_install,
    installs_advice,
    reinstall_command,
)

HOME = Path("/home/me")
ROOTS = InstallRoots(
    uv_tools=(HOME / ".local/share/uv/tools",),
    pipx_homes=(HOME / ".local/pipx",),
)
HOMEBREW = Install(
    InstallKind.HOMEBREW,
    Path("/opt/homebrew/Cellar/cstudy/0.11.1/libexec"),
    Path("/opt/homebrew/bin/cstudy"),
    "0.11.1",
)
UV_OLD = Install(
    InstallKind.UV_TOOL,
    HOME / ".local/share/uv/tools/coding-study",
    HOME / ".local/bin/cstudy",
    "0.1.0",
)
PIPX = Install(
    InstallKind.PIPX,
    HOME / ".local/pipx/venvs/coding-study",
    HOME / ".local/bin/cstudy",
    "0.9.0",
)
CHECKOUT = Install(
    InstallKind.OTHER,
    Path("/src/coding-study/.venv"),
    Path("/src/coding-study/.venv/bin/cstudy"),
    "0.11.1",
)


def scan(*on_path: Install, running: Install | None = None) -> InstallScan:
    return InstallScan(on_path, running or on_path[0], HOME)


@pytest.mark.parametrize(
    ("prefix", "kind"),
    [
        ("/opt/homebrew/Cellar/cstudy/0.11.1/libexec", InstallKind.HOMEBREW),
        ("/home/linuxbrew/.linuxbrew/Cellar/cstudy/0.11.1/libexec", InstallKind.HOMEBREW),
        ("/usr/local/Cellar/cstudy/0.11.1/libexec", InstallKind.HOMEBREW),
        ("/home/me/.local/share/uv/tools/coding-study", InstallKind.UV_TOOL),
        ("/home/me/.local/pipx/venvs/coding-study", InstallKind.PIPX),
        ("/home/me/src/coding-study/.venv", InstallKind.OTHER),
        ("/opt/homebrew/Cellar/other/1.0/libexec", InstallKind.OTHER),
        ("/home/me/.local/share/uv/tools/another-tool", InstallKind.OTHER),
    ],
)
def test_an_install_is_classified_by_where_its_environment_lives(prefix, kind):
    assert classify_install(Path(prefix), ROOTS) == kind


def test_a_custom_uv_tool_directory_and_pipx_home_classify_too():
    roots = InstallRoots(uv_tools=(Path("/data/uv"),), pipx_homes=(Path("/data/pipx"),))
    assert (
        classify_install(Path("/data/uv/coding-study"), roots),
        classify_install(Path("/data/pipx/venvs/coding-study"), roots),
    ) == (InstallKind.UV_TOOL, InstallKind.PIPX)


def test_one_install_is_reported_with_its_kind_version_and_path():
    advice = installs_advice(scan(HOMEBREW))
    assert (advice.detail, advice.fix) == ("Homebrew 0.11.1 (/opt/homebrew/bin/cstudy)", None)


def test_a_path_under_home_is_shown_with_a_tilde():
    assert installs_advice(scan(UV_OLD)).detail == "uv tool 0.1.0 (~/.local/bin/cstudy)"


def test_an_install_without_metadata_has_an_unknown_version():
    unknown = Install(InstallKind.OTHER, Path("/x"), Path("/x/bin/cstudy"), None)
    assert installs_advice(scan(unknown)).detail == "other, version unknown (/x/bin/cstudy)"


def test_no_cstudy_on_path_reports_the_running_install_only():
    running = Install(InstallKind.OTHER, Path("/src/.venv"), None, "0.11.1")
    advice = installs_advice(InstallScan((), running, HOME))
    assert (advice.detail, advice.fix) == (
        "none on PATH; this doctor is other 0.11.1 (/src/.venv)",
        None,
    )


def test_the_incident_two_installs_with_the_older_one_running_first():
    advice = installs_advice(scan(UV_OLD, HOMEBREW))
    assert advice.detail == (
        "2 cstudy installs on PATH: uv tool 0.1.0 (~/.local/bin/cstudy) runs first; "
        "Homebrew 0.11.1 (/opt/homebrew/bin/cstudy) is shadowed"
    )
    assert advice.fix == (
        "keep Homebrew 0.11.1, the newest (uv tool 0.1.0 runs first and is older); "
        "uninstall the others: uv tool uninstall coding-study"
    )


def test_the_newest_install_running_first_is_the_one_to_keep():
    advice = installs_advice(scan(HOMEBREW, PIPX))
    assert advice.fix == (
        "keep Homebrew 0.11.1, which runs first; uninstall the others: pipx uninstall coding-study"
    )


def test_each_other_install_gets_its_own_removal_command():
    advice = installs_advice(scan(HOMEBREW, UV_OLD, PIPX))
    assert advice.fix is not None
    assert advice.fix.endswith(
        "uninstall the others: uv tool uninstall coding-study; pipx uninstall coding-study"
    )
    assert advice.detail.startswith("3 cstudy installs on PATH: Homebrew 0.11.1")
    assert advice.detail.endswith(
        "uv tool 0.1.0 (~/.local/bin/cstudy) is shadowed; "
        "pipx 0.9.0 (~/.local/bin/cstudy) is shadowed"
    )


def test_removing_a_homebrew_install_uses_brew():
    advice = installs_advice(scan(UV_OLD, HOMEBREW, PIPX))
    assert advice.fix is not None
    assert advice.fix.endswith(
        "uninstall the others: uv tool uninstall coding-study; pipx uninstall coding-study"
    )
    newer_pipx = replace(PIPX, version="1.0.0")
    assert str(installs_advice(scan(HOMEBREW, newer_pipx)).fix).endswith("brew uninstall cstudy")


def test_another_install_is_removed_by_taking_its_directory_off_path():
    advice = installs_advice(scan(HOMEBREW, CHECKOUT))
    assert advice.fix == (
        "keep Homebrew 0.11.1, which runs first; "
        "uninstall the others: remove /src/coding-study/.venv/bin from PATH"
    )


def test_the_same_versions_keep_the_one_that_runs_first():
    twin = Install(InstallKind.PIPX, PIPX.prefix, PIPX.executable, "0.11.1")
    advice = installs_advice(scan(twin, HOMEBREW))
    assert advice.fix is not None
    assert advice.fix.startswith("keep pipx 0.11.1, which runs first")


def test_an_unknown_version_never_outranks_a_known_one():
    unknown = Install(InstallKind.UV_TOOL, UV_OLD.prefix, UV_OLD.executable, None)
    advice = installs_advice(scan(unknown, HOMEBREW))
    assert advice.fix is not None
    assert advice.fix.startswith("keep Homebrew 0.11.1, the newest (uv tool runs first")


def test_a_doctor_that_is_not_the_first_install_says_which_one_it_is():
    advice = installs_advice(scan(UV_OLD, HOMEBREW, running=HOMEBREW))
    assert advice.detail.endswith("; this doctor is Homebrew 0.11.1")


def test_a_doctor_outside_path_is_named_beside_the_one_install():
    running = Install(InstallKind.OTHER, Path("/src/.venv"), None, "0.12.0")
    advice = installs_advice(InstallScan((HOMEBREW,), running, HOME))
    assert advice.detail == (
        "Homebrew 0.11.1 (/opt/homebrew/bin/cstudy); this doctor is other 0.12.0 (/src/.venv)"
    )


@pytest.mark.parametrize(
    ("running", "command"),
    [
        (HOMEBREW, "brew reinstall cstudy"),
        (UV_OLD, "uv tool install --reinstall coding-study"),
        (PIPX, "pipx reinstall coding-study"),
        (CHECKOUT, "reinstall cstudy"),
    ],
)
def test_the_reinstall_hint_names_the_running_install(running, command):
    assert reinstall_command(scan(running)) == command


def test_an_editable_uv_tool_is_reinstalled_from_its_source():
    editable = Install(
        InstallKind.UV_TOOL,
        UV_OLD.prefix,
        UV_OLD.executable,
        "0.1.0",
        Path("/src/my cstudy/cli"),
        True,
    )
    assert reinstall_command(scan(editable)) == (
        "uv tool install --reinstall --editable '/src/my cstudy/cli'"
    )


def test_a_uv_tool_built_from_a_directory_is_reinstalled_from_it():
    local = Install(
        InstallKind.UV_TOOL, UV_OLD.prefix, UV_OLD.executable, "0.1.0", Path("/src/cli")
    )
    assert reinstall_command(scan(local)) == "uv tool install --reinstall /src/cli"


def test_the_reinstall_hint_points_at_the_installs_row_when_several_exist():
    command = reinstall_command(scan(UV_OLD, HOMEBREW, running=UV_OLD))
    assert command == (
        "uv tool install --reinstall coding-study (several cstudy installs: see the installs row)"
    )


def test_the_reinstall_hint_can_point_at_cstudy_doctor_instead():
    command = reinstall_command(scan(UV_OLD, HOMEBREW, running=UV_OLD), "see cstudy doctor")
    assert command.endswith("(several cstudy installs: see cstudy doctor)")


def test_the_reinstall_hint_names_the_running_install_even_when_it_is_shadowed():
    assert reinstall_command(scan(UV_OLD, HOMEBREW, running=HOMEBREW)).startswith(
        "brew reinstall cstudy"
    )
