"""Which server `cstudy serve` may start ahead of time (docs/specs/web-ui.md#warm-up): the default
language's, rooted in its practice project, on this machine, only while code intelligence is on
and the server is usable; no other language, and no sidecar."""

from pathlib import Path

import pytest

from coding_study.application.code_intelligence import SessionTarget, warm_up_target
from coding_study.application.environment import Environment
from coding_study.domain.code_intelligence import WARM_IDLE_S
from coding_study.domain.config import Config
from coding_study.domain.preferences import Preferences
from coding_study.domain.problem import Language
from tests.fakes import (
    INSTALLED_SERVERS,
    JDK_HOME,
    FakeLanguageServers,
    jdk_of,
    make_environment,
    repository_root,
)
from tests.helpers import FIXTURE_TRACKS

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
ON = Preferences(code_intelligence=True)


def environment(
    tmp_path: Path,
    language: Language = Language.PYTHON,
    servers: FakeLanguageServers | None = None,
    jdk: int = 25,
) -> Environment:
    return make_environment(
        repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS),
        config=Config(default_lang=language),
        language_servers=servers or FakeLanguageServers(INSTALLED_SERVERS),
        jdk=jdk_of(jdk),
    )


def target(found: SessionTarget | None) -> SessionTarget:
    assert found is not None
    return found


def test_with_code_intelligence_off_nothing_is_warmed(tmp_path):
    assert warm_up_target(environment(tmp_path), Preferences()) is None


@pytest.mark.parametrize(
    ("language", "server", "root"),
    [
        (Language.PYTHON, "basedpyright", "python"),
        (Language.TYPESCRIPT, "typescript-language-server", "typescript"),
        (Language.GO, "gopls", "go"),
        (Language.RUST, "rust-analyzer", "rust"),
    ],
)
def test_the_default_languages_server_is_warmed_in_its_practice_project(
    tmp_path, language, server, root
):
    found = target(warm_up_target(environment(tmp_path, language), ON))

    assert (found.server.name, found.root) == (server, root)


def test_a_warmed_server_runs_on_this_machine(tmp_path):
    assert target(warm_up_target(environment(tmp_path), ON)).sidecar is None


def test_a_server_that_is_not_installed_is_not_warmed(tmp_path):
    found = warm_up_target(environment(tmp_path, servers=FakeLanguageServers({})), ON)

    assert found is None


def test_java_is_warmed_on_the_selected_jdk_25(tmp_path):
    found = target(warm_up_target(environment(tmp_path, Language.JAVA), ON))

    assert (found.server.name, found.root, found.java_home) == ("jdtls", "jvm", JDK_HOME)


def test_java_is_not_warmed_on_a_jdk_it_cannot_run_on(tmp_path):
    assert warm_up_target(environment(tmp_path, Language.JAVA, jdk=21), ON) is None


def test_kotlin_is_not_warmed_before_its_license_is_accepted(tmp_path):
    servers = FakeLanguageServers(INSTALLED_SERVERS)
    servers.accepted.clear()

    assert warm_up_target(environment(tmp_path, Language.KOTLIN, servers), ON) is None


def test_a_warmed_server_waits_about_ten_minutes_for_an_editor():
    assert WARM_IDLE_S == 600
