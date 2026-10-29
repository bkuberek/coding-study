from coding_study.adapters.languages.go.toolchain import build_environment

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
