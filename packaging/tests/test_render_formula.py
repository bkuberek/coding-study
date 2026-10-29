import pytest
from render_formula import TEMPLATE, ReleaseFiles, main, render_formula

BASE_URL = "https://github.com/bkuberek/coding-study/releases/download/v0.4.0"
WHEEL_NAME = "coding_study-0.4.0-py3-none-any.whl"
SHA256_OF_ABC = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
SHA256_OF_EMPTY = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
FIELDS = "${wheel_name}|${wheel_url}|${wheel_sha256}|${requirements_url}|${requirements_sha256}"


@pytest.fixture
def release(tmp_path):
    wheel = tmp_path / WHEEL_NAME
    wheel.write_bytes(b"abc")
    requirements = tmp_path / "requirements.txt"
    requirements.write_bytes(b"")
    return ReleaseFiles(BASE_URL, wheel, requirements)


def test_fields_name_the_files_under_the_base_url(release):
    assert render_formula(release, FIELDS).split("|") == [
        WHEEL_NAME,
        f"{BASE_URL}/{WHEEL_NAME}",
        SHA256_OF_ABC,
        f"{BASE_URL}/requirements.txt",
        SHA256_OF_EMPTY,
    ]


def test_trailing_slash_of_the_base_url_is_ignored(release):
    with_slash = ReleaseFiles(BASE_URL + "/", release.wheel, release.requirements)
    assert render_formula(with_slash, "${wheel_url}") == f"{BASE_URL}/{WHEEL_NAME}"


def test_unknown_placeholder_raises(release):
    with pytest.raises(KeyError, match="version"):
        render_formula(release, "${version}")


def test_platform_wheel_is_rejected(release, tmp_path):
    platform_wheel = tmp_path / "coding_study-0.4.0-cp313-cp313-macosx_11_0_arm64.whl"
    platform_wheel.write_bytes(b"abc")
    with pytest.raises(ValueError, match="not a pure-Python wheel"):
        render_formula(ReleaseFiles(BASE_URL, platform_wheel, release.requirements), FIELDS)


def test_requirements_under_another_name_are_rejected(release, tmp_path):
    other = tmp_path / "runtime.txt"
    other.write_bytes(b"")
    with pytest.raises(ValueError, match=r"must be named requirements\.txt"):
        render_formula(ReleaseFiles(BASE_URL, release.wheel, other), FIELDS)


def test_template_renders_every_placeholder(release):
    formula = render_formula(release, TEMPLATE.read_text(encoding="utf-8"))
    assert "${" not in formula


def test_template_installs_the_wheel_it_downloads(release):
    formula = render_formula(release, TEMPLATE.read_text(encoding="utf-8"))
    assert f'url "{BASE_URL}/{WHEEL_NAME}"' in formula
    assert f'venv.pip_install buildpath/"{WHEEL_NAME}"' in formula


def test_main_writes_the_formula(release, tmp_path):
    output = tmp_path / "Formula" / "cstudy.rb"
    main(
        [
            "--base-url",
            BASE_URL,
            "--wheel",
            str(release.wheel),
            "--requirements",
            str(release.requirements),
            "--output",
            str(output),
        ]
    )
    assert f'sha256 "{SHA256_OF_ABC}"' in output.read_text(encoding="utf-8")
