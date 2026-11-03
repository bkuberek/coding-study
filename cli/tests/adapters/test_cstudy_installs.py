"""The `cstudy` installs on PATH, found in fake layouts built under a temporary directory:
a `<prefix>/bin/cstudy` script, the package metadata under the prefix's site-packages, and a
`bin` directory of symlinks, as Homebrew, uv and pipx leave them."""

from collections.abc import Mapping
from pathlib import Path

from coding_study.adapters.cstudy_installs import PathCstudyInstalls
from coding_study.application.installs import Install, InstallKind


def make_install(prefix: Path, version: str | None = "0.11.1", metadata: bool = True) -> Path:
    """A virtual environment with a `cstudy` console script; returns the script."""
    script = prefix / "bin" / "cstudy"
    script.parent.mkdir(parents=True)
    script.write_text(f"#!{prefix}/bin/python\n")
    script.chmod(0o755)
    (prefix / "pyvenv.cfg").write_text("home = /usr/bin\n")
    if version is not None and metadata:
        dist_info = (
            prefix / "lib" / "python3.13" / "site-packages" / f"coding_study-{version}.dist-info"
        )
        dist_info.mkdir(parents=True)
        (dist_info / "METADATA").write_text(
            f"Metadata-Version: 2.4\nName: coding-study\nVersion: {version}\n\nDescription.\n"
        )
    return script


def link_into(bin_directory: Path, script: Path) -> Path:
    bin_directory.mkdir(parents=True, exist_ok=True)
    link = bin_directory / "cstudy"
    link.symlink_to(script)
    return link


def installs(
    tmp_path: Path,
    *path: Path,
    environ: Mapping[str, str] | None = None,
    running: Path | None = None,
):
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    variables = {"PATH": ":".join(str(directory) for directory in path), **(environ or {})}
    return PathCstudyInstalls(variables, home, running or tmp_path / "elsewhere", "0.11.1").scan()


def homebrew(tmp_path: Path, version: str = "0.11.1") -> tuple[Path, Path]:
    prefix = tmp_path / "brew" / "Cellar" / "cstudy" / version / "libexec"
    link = link_into(tmp_path / "brew" / "bin", make_install(prefix, version))
    return link, prefix


def uv_tool(tmp_path: Path, version: str = "0.1.0", tools: Path | None = None) -> tuple[Path, Path]:
    prefix = (tools or tmp_path / "home" / ".local" / "share" / "uv" / "tools") / "coding-study"
    link = link_into(tmp_path / "home" / ".local" / "bin", make_install(prefix, version))
    return link, prefix


def test_a_homebrew_install_is_classified_and_versioned_from_its_metadata(tmp_path):
    link, prefix = homebrew(tmp_path)
    found = installs(tmp_path, link.parent).on_path
    assert found == (Install(InstallKind.HOMEBREW, prefix.resolve(), link, "0.11.1"),)


def test_the_incident_uv_tool_first_then_homebrew(tmp_path):
    uv_link, _ = uv_tool(tmp_path)
    brew_link, _ = homebrew(tmp_path)
    found = installs(tmp_path, uv_link.parent, brew_link.parent).on_path
    assert [(i.kind, i.version, i.executable) for i in found] == [
        (InstallKind.UV_TOOL, "0.1.0", uv_link),
        (InstallKind.HOMEBREW, "0.11.1", brew_link),
    ]


def test_path_order_is_the_order_of_the_installs(tmp_path):
    uv_link, _ = uv_tool(tmp_path)
    brew_link, _ = homebrew(tmp_path)
    found = installs(tmp_path, brew_link.parent, uv_link.parent).on_path
    assert [i.kind for i in found] == [InstallKind.HOMEBREW, InstallKind.UV_TOOL]


def test_a_directory_listed_twice_counts_once(tmp_path):
    link, _ = homebrew(tmp_path)
    found = installs(tmp_path, link.parent, tmp_path / "empty", link.parent).on_path
    assert len(found) == 1


def test_symlinks_to_one_install_in_two_directories_count_once(tmp_path):
    link, prefix = homebrew(tmp_path)
    second = link_into(tmp_path / "other-bin", prefix / "bin" / "cstudy")
    found = installs(tmp_path, link.parent, second.parent).on_path
    assert [i.executable for i in found] == [link]


def test_a_directory_reached_through_a_symlink_counts_once(tmp_path):
    link, _ = homebrew(tmp_path)
    alias = tmp_path / "alias"
    alias.symlink_to(link.parent)
    assert len(installs(tmp_path, link.parent, alias).on_path) == 1


def test_pipx_is_classified_under_its_home(tmp_path):
    prefix = tmp_path / "home" / ".local" / "pipx" / "venvs" / "coding-study"
    link = link_into(tmp_path / "home" / ".local" / "bin", make_install(prefix, "0.9.0"))
    found = installs(tmp_path, link.parent).on_path
    assert [(i.kind, i.version) for i in found] == [(InstallKind.PIPX, "0.9.0")]


def test_pipx_home_names_another_pipx_directory(tmp_path):
    pipx_home = tmp_path / "pipx-data"
    prefix = pipx_home / "venvs" / "coding-study"
    link = link_into(tmp_path / "bin", make_install(prefix, "0.9.0"))
    found = installs(tmp_path, link.parent, environ={"PIPX_HOME": str(pipx_home)}).on_path
    assert [i.kind for i in found] == [InstallKind.PIPX]


def test_uv_tool_dir_names_another_uv_tools_directory(tmp_path):
    tools = tmp_path / "uv-data" / "tools"
    link, _ = uv_tool(tmp_path, tools=tools)
    found = installs(tmp_path, link.parent, environ={"UV_TOOL_DIR": str(tools)}).on_path
    assert [i.kind for i in found] == [InstallKind.UV_TOOL]


def test_xdg_data_home_moves_the_uv_tools_directory(tmp_path):
    data = tmp_path / "xdg"
    link, _ = uv_tool(tmp_path, tools=data / "uv" / "tools")
    found = installs(tmp_path, link.parent, environ={"XDG_DATA_HOME": str(data)}).on_path
    assert [i.kind for i in found] == [InstallKind.UV_TOOL]


def test_a_checkout_environment_is_another_install(tmp_path):
    script = make_install(tmp_path / "src" / ".venv", "0.12.0")
    found = installs(tmp_path, script.parent).on_path
    assert [(i.kind, i.version, i.prefix) for i in found] == [
        (InstallKind.OTHER, "0.12.0", script.parent.parent.resolve())
    ]


def test_an_install_without_package_metadata_has_no_version(tmp_path):
    script = make_install(tmp_path / "venv", metadata=False)
    assert installs(tmp_path, script.parent).on_path[0].version is None


def test_a_directory_without_cstudy_and_a_missing_one_are_skipped(tmp_path):
    (tmp_path / "empty").mkdir()
    assert installs(tmp_path, tmp_path / "empty", tmp_path / "missing").on_path == ()


def test_a_cstudy_that_is_not_executable_is_skipped(tmp_path):
    script = make_install(tmp_path / "venv")
    script.chmod(0o644)
    assert installs(tmp_path, script.parent).on_path == ()


def test_an_empty_path_finds_nothing(tmp_path):
    assert installs(tmp_path).on_path == ()


def test_an_editable_uv_tool_names_its_source_from_the_receipt(tmp_path):
    link, prefix = uv_tool(tmp_path)
    (prefix / "uv-receipt.toml").write_text(
        '[tool]\nrequirements = [{ name = "coding-study", editable = "/src/coding-study/cli" }]\n'
    )
    found = installs(tmp_path, link.parent).on_path[0]
    assert (found.source, found.editable) == (Path("/src/coding-study/cli"), True)


def test_a_uv_tool_built_from_a_directory_names_it_without_editable(tmp_path):
    link, prefix = uv_tool(tmp_path)
    (prefix / "uv-receipt.toml").write_text(
        '[tool]\nrequirements = [{ name = "coding-study", directory = "/src/cli" }]\n'
    )
    found = installs(tmp_path, link.parent).on_path[0]
    assert (found.source, found.editable) == (Path("/src/cli"), False)


def test_an_unreadable_receipt_names_no_source(tmp_path):
    link, prefix = uv_tool(tmp_path)
    (prefix / "uv-receipt.toml").write_text("not [ toml")
    assert installs(tmp_path, link.parent).on_path[0].source is None


def test_the_running_install_is_the_one_on_path_with_the_same_environment(tmp_path):
    uv_link, _ = uv_tool(tmp_path)
    brew_link, brew_prefix = homebrew(tmp_path)
    scan = installs(tmp_path, uv_link.parent, brew_link.parent, running=brew_prefix)
    assert scan.running == scan.on_path[1]


def test_the_running_install_is_found_through_a_symlinked_prefix(tmp_path):
    brew_link, brew_prefix = homebrew(tmp_path)
    alias = tmp_path / "opt-cstudy"
    alias.symlink_to(brew_prefix)
    scan = installs(tmp_path, brew_link.parent, running=alias)
    assert scan.running == scan.on_path[0]


def test_a_running_install_outside_path_is_classified_from_its_prefix(tmp_path):
    _, uv_prefix = uv_tool(tmp_path)
    brew_link, _ = homebrew(tmp_path)
    scan = installs(tmp_path, brew_link.parent, running=uv_prefix)
    assert (scan.running.kind, scan.running.executable, scan.running.version) == (
        InstallKind.UV_TOOL,
        None,
        "0.11.1",
    )


def test_the_scan_carries_the_home_directory_for_display(tmp_path):
    assert installs(tmp_path).home == tmp_path / "home"
