from coding_study.adapters.languages.rust.toolchain import build_environment

USER = {
    "PATH": "/usr/bin",
    "RUSTFLAGS": "-C target-cpu=native",
    "CARGO_TARGET_DIR": "/elsewhere",
    "CARGO_BUILD_TARGET": "wasm32-unknown-unknown",
    "CARGO_PROFILE_RELEASE_OVERFLOW_CHECKS": "false",
    "RUSTC_WRAPPER": "sccache",
}


def test_the_users_build_settings_are_left_out():
    environment = build_environment(USER, {})
    left = {"RUSTFLAGS", "CARGO_TARGET_DIR", "CARGO_BUILD_TARGET"} & environment.keys()
    assert (left, "CARGO_PROFILE_RELEASE_OVERFLOW_CHECKS" in environment) == (set(), False)


def test_rustflags_and_wrappers_are_pinned_empty():
    environment = build_environment(USER, {})
    pinned = ("CARGO_ENCODED_RUSTFLAGS", "RUSTC_WRAPPER", "RUSTC_WORKSPACE_WRAPPER")
    assert [environment[name] for name in pinned] == ["", "", ""]


def test_the_build_settings_win():
    environment = build_environment(USER, {"CARGO_TARGET_DIR": "/ws/.cs/build/rust/target"})
    assert (environment["CARGO_TARGET_DIR"], environment["PATH"]) == (
        "/ws/.cs/build/rust/target",
        "/usr/bin",
    )
