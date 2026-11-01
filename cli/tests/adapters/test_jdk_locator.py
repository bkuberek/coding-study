"""The JDK the shell selects: `JAVA_HOME`, else the first `java` on `PATH`, with its version from
the home's `release` file (docs/specs/cli.md#the-selected-jdk). Fake JDK homes stand in for real
ones: a `bin/java` script and, unless left out, a `release` file."""

from pathlib import Path

import pytest

from coding_study.adapters.jdk_locator import EnvJdkSelector
from coding_study.domain.errors import RunnerStartError
from coding_study.domain.jdk import JdkSource, SelectedJdk

PROBE_COUNT = "probes.txt"


def fake_jdk(home: Path, version: str | None = "26.0.1", probed_version: str = "25.0.5") -> Path:
    """A JDK home; its `java` answers `-XshowSettings:properties` with `probed_version` and counts
    how often it ran in `<home>/probes.txt`."""
    (home / "bin").mkdir(parents=True)
    java = home / "bin" / "java"
    java.write_text(
        "#!/bin/sh\n"
        f"echo run >> '{home / PROBE_COUNT}'\n"
        f"echo '    java.home = {home}' >&2\n"
        f"echo '    java.version = {probed_version}' >&2\n"
    )
    java.chmod(0o755)
    if version is not None:
        (home / "release").write_text(f'IMPLEMENTOR="Someone"\nJAVA_VERSION="{version}"\n')
    return home


def stub_java(directory: Path, home: Path) -> Path:
    """A launcher stub, as some systems put on PATH: it is no JDK's `bin/java`, and names the home
    it runs from only when asked."""
    directory.mkdir(parents=True)
    java = directory / "java"
    java.write_text(
        f"#!/bin/sh\necho '    java.home = {home}' >&2\necho '    java.version = 1' >&2\n"
    )
    java.chmod(0o755)
    return java


def on_path(directory: Path) -> dict[str, str]:
    """Only `directory`: the system's directories may hold a real `java`. The fake scripts use
    shell builtins only."""
    return {"PATH": str(directory)}


def linked_java(tmp_path: Path, home: Path) -> Path:
    """A directory on PATH whose `java` links to the home's, as version managers and package
    managers install it."""
    directory = tmp_path / "path-bin"
    directory.mkdir()
    (directory / "java").symlink_to(home / "bin" / "java")
    return directory


def test_java_home_selects_its_jdk(tmp_path):
    home = fake_jdk(tmp_path / "jdk-26")
    selector = EnvJdkSelector({"JAVA_HOME": str(home)})
    assert selector.selected() == SelectedJdk("26.0.1", 26, JdkSource.JAVA_HOME)


def test_java_home_outranks_the_java_on_path(tmp_path):
    home = fake_jdk(tmp_path / "jdk-26")
    other = fake_jdk(tmp_path / "jdk-21", "21.0.13")
    environ = {"JAVA_HOME": str(home), **on_path(other / "bin")}
    assert EnvJdkSelector(environ).home() == home.resolve()


def test_without_java_home_the_java_on_path_selects_its_jdk(tmp_path):
    home = fake_jdk(tmp_path / "jdk-21", "21.0.13")
    selector = EnvJdkSelector(on_path(home / "bin"))
    assert selector.selected() == SelectedJdk("21.0.13", 21, JdkSource.PATH)


def test_a_linked_java_on_path_selects_the_jdk_it_links_to(tmp_path):
    home = fake_jdk(tmp_path / "jdk-26")
    selector = EnvJdkSelector(on_path(linked_java(tmp_path, home)))
    assert selector.home() == home.resolve()


def test_the_version_of_a_linked_java_comes_from_its_home(tmp_path):
    home = fake_jdk(tmp_path / "jdk-26")
    selector = EnvJdkSelector(on_path(linked_java(tmp_path, home)))
    assert selector.selected() == SelectedJdk("26.0.1", 26, JdkSource.PATH)


def test_a_jdk_with_a_release_file_is_never_run(tmp_path):
    home = fake_jdk(tmp_path / "jdk-26")
    EnvJdkSelector({"JAVA_HOME": str(home)}).selected()
    assert not (home / PROBE_COUNT).exists()


def test_an_empty_java_home_counts_as_unset(tmp_path):
    home = fake_jdk(tmp_path / "jdk-21", "21.0.13")
    selector = EnvJdkSelector({"JAVA_HOME": "", **on_path(home / "bin")})
    assert selector.selected() == SelectedJdk("21.0.13", 21, JdkSource.PATH)


def test_a_java_home_without_a_java_selects_nothing(tmp_path):
    empty = tmp_path / "not-a-jdk"
    empty.mkdir()
    assert EnvJdkSelector({"JAVA_HOME": str(empty)}).selected() is None


def test_a_java_home_without_a_java_does_not_fall_back_to_path(tmp_path):
    home = fake_jdk(tmp_path / "jdk-21", "21.0.13")
    environ = {"JAVA_HOME": str(tmp_path / "missing"), **on_path(home / "bin")}
    assert EnvJdkSelector(environ).selected() is None


def test_a_java_home_without_a_java_is_reported_as_set(tmp_path):
    missing = str(tmp_path / "missing")
    assert EnvJdkSelector({"JAVA_HOME": missing}).unusable_java_home() == missing


def test_a_usable_java_home_is_not_reported(tmp_path):
    home = fake_jdk(tmp_path / "jdk-26")
    assert EnvJdkSelector({"JAVA_HOME": str(home)}).unusable_java_home() is None


def test_no_java_home_and_no_java_on_path_selects_nothing(tmp_path):
    assert EnvJdkSelector(on_path(tmp_path)).selected() is None


def test_no_jdk_found_reports_no_java_home(tmp_path):
    assert EnvJdkSelector(on_path(tmp_path)).unusable_java_home() is None


def test_a_home_without_a_release_file_is_asked_for_its_version(tmp_path):
    home = fake_jdk(tmp_path / "jdk", version=None, probed_version="25.0.5")
    selector = EnvJdkSelector({"JAVA_HOME": str(home)})
    assert selector.selected() == SelectedJdk("25.0.5", 25, JdkSource.JAVA_HOME)


def test_a_launcher_stub_on_path_is_asked_for_its_home(tmp_path):
    home = fake_jdk(tmp_path / "jdk-26")
    stub = stub_java(tmp_path / "usr-bin", home)
    assert EnvJdkSelector(on_path(stub.parent)).home() == home.resolve()


def test_the_version_behind_a_launcher_stub_comes_from_its_home(tmp_path):
    home = fake_jdk(tmp_path / "jdk-26")
    stub = stub_java(tmp_path / "usr-bin", home)
    selector = EnvJdkSelector(on_path(stub.parent))
    assert selector.selected() == SelectedJdk("26.0.1", 26, JdkSource.PATH)


def test_a_java_that_does_not_run_selects_nothing(tmp_path):
    directory = tmp_path / "usr-bin"
    directory.mkdir()
    (directory / "java").write_text(
        "#!/bin/sh\necho 'Unable to locate a Java Runtime.' >&2\nexit 1\n"
    )
    (directory / "java").chmod(0o755)
    assert EnvJdkSelector(on_path(directory)).selected() is None


def test_a_jdk_is_asked_at_most_once_per_selector(tmp_path):
    home = fake_jdk(tmp_path / "jdk", version=None)
    selector = EnvJdkSelector({"JAVA_HOME": str(home)})
    selector.selected()
    selector.home()
    assert (home / PROBE_COUNT).read_text().splitlines() == ["run"]


@pytest.mark.parametrize(
    ("version", "feature"),
    [("27", 27), ("26.0.2.1", 26), ("21.0.13", 21), ("17.0.9", 17), ("1.8.0_392", 8)],
)
def test_the_feature_release_is_read_from_the_version(tmp_path, version, feature):
    home = fake_jdk(tmp_path / "jdk", version)
    selected = EnvJdkSelector({"JAVA_HOME": str(home)}).selected()
    assert selected == SelectedJdk(version, feature, JdkSource.JAVA_HOME)


def test_no_jdk_found_has_no_home(tmp_path):
    with pytest.raises(RunnerStartError, match="no JDK was found"):
        EnvJdkSelector(on_path(tmp_path)).home()


def test_a_java_home_without_a_jdk_has_no_home(tmp_path):
    missing = tmp_path / "missing"
    with pytest.raises(RunnerStartError, match=rf"JAVA_HOME \({missing}\) holds no JDK"):
        EnvJdkSelector({"JAVA_HOME": str(missing)}).home()
