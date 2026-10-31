import pytest

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


@pytest.mark.parametrize(
    "name",
    [
        "RUSTC",
        "RUSTDOC",
        "RUSTDOCFLAGS",
        "RUSTC_BOOTSTRAP",
        "CARGO_INCREMENTAL",
        "CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER",
        "CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_RUSTFLAGS",
        "CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_RUNNER",
        "CARGO_TERM_COLOR",
        "CARGO_UNSTABLE_BUILD_STD",
    ],
)
def test_the_users_compiler_linker_and_output_settings_are_left_out(name):
    assert name not in build_environment({**USER, name: "x"}, {})


def test_what_the_build_needs_from_the_users_environment_stays():
    user = {
        "PATH": "/usr/bin",
        "HOME": "/h",
        "HTTPS_PROXY": "http://proxy",
        "CARGO_HOME": "/cargo",
        "RUSTUP_HOME": "/rustup",
        "RUSTUP_TOOLCHAIN": "stable",
    }
    kept = build_environment(user, {})
    assert {name: kept[name] for name in user} == user
