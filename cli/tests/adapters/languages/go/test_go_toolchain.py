import pytest

from coding_study.adapters.languages.go.toolchain import (
    GO_ENVIRONMENT,
    UNSET_PLATFORM_SETTINGS,
    build_environment,
)

USER = {"PATH": "/usr/bin", "GOOS": "windows", "GOARCH": "386", "GOFLAGS": "-mod=mod"}


def test_the_users_platform_settings_are_left_out():
    environment = build_environment(USER, {})
    assert ("GOOS" in environment, "GOARCH" in environment) == (False, False)


def test_the_users_go_env_file_and_flags_are_ignored():
    environment = build_environment(USER, {})
    assert (environment["GOENV"], environment["GOFLAGS"]) == ("off", "-mod=readonly")


def test_the_build_settings_win():
    environment = build_environment({**USER, "GOWORK": "/elsewhere/go.work"}, {"GOWORK": "w"})
    assert (environment["GOWORK"], environment["PATH"]) == ("w", "/usr/bin")


def test_cgo_is_off_and_the_users_c_compiler_and_cgo_settings_are_left_out():
    user = {**USER, "CGO_ENABLED": "1", "CGO_CFLAGS": "-O3", "CC": "/opt/gcc", "CXX": "g++"}
    environment = build_environment(user, {})
    left = {"CGO_CFLAGS", "CC", "CXX"} & environment.keys()
    assert (environment["CGO_ENABLED"], left) == ("0", set())


@pytest.mark.parametrize(
    "name", ["GOEXPERIMENT", "GOAMD64", "GOARM", "GOARM64", "GO386", "GOMIPS", "GOFIPS140"]
)
def test_the_users_experiments_and_instruction_set_levels_are_left_out(name):
    assert name not in build_environment({**USER, name: "v3"}, {})


def test_what_the_build_needs_from_the_users_environment_stays():
    user = {"PATH": "/usr/bin", "HTTPS_PROXY": "http://proxy", "GOCACHE": "/cache", "HOME": "/h"}
    assert build_environment(user, {}) == {**user, **GO_ENVIRONMENT}


def test_a_process_started_later_blanks_the_platform_settings():
    blanked = {"GOOS", "GOARCH", "GOEXPERIMENT", "GOAMD64"} & UNSET_PLATFORM_SETTINGS.keys()
    assert (blanked, set(UNSET_PLATFORM_SETTINGS.values())) == (
        {"GOOS", "GOARCH", "GOEXPERIMENT", "GOAMD64"},
        {""},
    )
