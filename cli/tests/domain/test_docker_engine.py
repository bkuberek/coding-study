"""What each state of the Docker engine means to someone who starts a service project."""

import pytest

from coding_study.domain.docker_engine import (
    INSTALL_REACHES,
    EngineState,
    EngineStatus,
    engine_problem,
    install_message,
    no_permission_message,
)

MACOS = "darwin"
LINUX = "linux"


def test_a_running_engine_has_no_problem():
    assert engine_problem(EngineState(EngineStatus.RUNNING, "29.9.2", "5.6.1"), MACOS) is None


def test_a_stopped_engine_is_a_problem_only_until_cstudy_has_tried_to_start_it():
    problem = engine_problem(EngineState(EngineStatus.STOPPED), MACOS)

    assert problem is not None
    assert "did not start" in problem


@pytest.mark.parametrize("status", [EngineStatus.NOT_INSTALLED, EngineStatus.NO_COMPOSE])
def test_a_missing_engine_or_compose_gives_the_install_message(status):
    assert engine_problem(EngineState(status), MACOS) == install_message(MACOS)


def test_no_permission_has_a_message_of_its_own():
    assert engine_problem(EngineState(EngineStatus.NO_PERMISSION), LINUX) == no_permission_message()


def test_no_permission_names_the_group_and_what_it_means():
    message = no_permission_message()

    assert "docker group" in message
    assert "effectively root" in message
    assert "sudo usermod" in message


@pytest.mark.parametrize("platform", [MACOS, LINUX])
def test_the_install_message_links_the_install_page(platform):
    assert "https://docs.docker.com/" in install_message(platform)


def test_the_macos_message_names_docker_desktop_and_its_license_terms():
    message = install_message(MACOS)

    assert "Docker Desktop" in message
    assert "larger companies" in message
    assert "desktop-license" in message


def test_the_linux_message_says_the_group_is_effectively_root():
    assert "effectively root" in install_message(LINUX)


@pytest.mark.parametrize("platform", [MACOS, LINUX])
def test_the_install_message_says_install_reaches_the_lan_and_loopback(platform):
    assert INSTALL_REACHES in install_message(platform)
    assert "your LAN" in INSTALL_REACHES
    assert "loopback" in INSTALL_REACHES


@pytest.mark.parametrize("platform", [MACOS, LINUX])
def test_no_message_recommends_changing_an_engine_setting(platform):
    message = install_message(platform).lower()

    assert "memory" not in message
    assert "settings" not in message


def test_a_status_says_it_is_running():
    assert EngineState(EngineStatus.RUNNING).running
    assert not EngineState(EngineStatus.STOPPED).running
