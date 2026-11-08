"""Reading JetBrains' Kotlin LSP releases (ADR 0018, Kotlin revisited): the newest build for a
machine from the GitHub releases list, its SHA-256 from the `.sha256` file JetBrains publishes
beside it, the license of its release, and the last day its early-access license runs."""

from datetime import date

import pytest

from coding_study.domain.code_intelligence import KOTLIN_LSP, KOTLIN_LSP_LICENSE, License
from coding_study.domain.server_builds import (
    Build,
    checksum_in,
    expired_already,
    last_day,
    license_of,
    newest_build,
)

RELEASES = KOTLIN_LSP.releases
DOWNLOADS = "https://download.jetbrains.com/language-server/kotlin-server"
SHA = "b403bf8a54bd458e3ba6731cf8abb3340be08b439c03576dfc02b13faf3694b8"


def body(version: str, *files: str, checksums: bool = True) -> str:
    """A release's notes as JetBrains writes them: each download beside its checksum link."""
    lines = []
    for file in files:
        url = f"{DOWNLOADS}/{version}/{file}"
        checksum = f" | [SHA-256 checksum]({url}.sha256)" if checksums else ""
        lines.append(f"* [Download]({url}){checksum}")
    return "\n".join(lines)


def release(version: str, *files: str, draft: bool = False, checksums: bool = True) -> dict:
    return {
        "tag_name": f"kotlin-lsp/v{version}",
        "draft": draft,
        "body": body(version, *files, checksums=checksums),
    }


ALL_FILES = (
    "kotlin-server-{v}.sit",
    "kotlin-server-{v}-aarch64.sit",
    "kotlin-server-{v}.tar.gz",
    "kotlin-server-{v}-aarch64.tar.gz",
    "kotlin-server-{v}.win.zip",
    "kotlin-server-{v}-aarch64.win.zip",
)


def full_release(version: str, **kwargs) -> dict:
    return release(version, *(file.format(v=version) for file in ALL_FILES), **kwargs)


def newest(document: object, machine: str = "darwin-arm64") -> Build | None:
    assert RELEASES is not None
    return newest_build(document, RELEASES, machine)


def test_the_newest_release_is_chosen():
    found = newest([full_release("263.7084.0"), full_release("263.6379.0")])
    assert found is not None
    assert (found.version, found.tag) == ("263.7084.0", "kotlin-lsp/v263.7084.0")


def test_the_list_is_read_newest_first_as_github_orders_it():
    found = newest([full_release("263.6379.0"), full_release("263.7084.0")])
    assert found is not None
    assert found.version == "263.6379.0"


@pytest.mark.parametrize(
    ("machine", "file"),
    [
        ("darwin-arm64", "kotlin-server-263.7084.0-aarch64.sit"),
        ("darwin-x64", "kotlin-server-263.7084.0.sit"),
        ("linux-x64", "kotlin-server-263.7084.0.tar.gz"),
        ("linux-arm64", "kotlin-server-263.7084.0-aarch64.tar.gz"),
        ("win32-x64", "kotlin-server-263.7084.0.win.zip"),
        ("win32-arm64", "kotlin-server-263.7084.0-aarch64.win.zip"),
    ],
)
def test_each_machine_gets_its_own_standalone_archive(machine, file):
    found = newest([full_release("263.7084.0")], machine)
    assert found is not None
    assert (found.url, found.checksum_url) == (
        f"{DOWNLOADS}/263.7084.0/{file}",
        f"{DOWNLOADS}/263.7084.0/{file}.sha256",
    )


def test_a_draft_is_skipped():
    found = newest([full_release("263.9000.0", draft=True), full_release("263.7084.0")])
    assert found is not None
    assert found.version == "263.7084.0"


def test_a_release_without_the_archive_of_this_machine_is_skipped():
    linux_only = release("263.9000.0", "kotlin-server-263.9000.0.tar.gz")
    found = newest([linux_only, full_release("263.7084.0")])
    assert found is not None
    assert found.version == "263.7084.0"


def test_an_archive_without_a_published_checksum_is_skipped():
    """Nothing is downloaded that JetBrains publishes no checksum for."""
    unchecked = full_release("263.9000.0", checksums=False)
    found = newest([unchecked, full_release("263.7084.0")])
    assert found is not None
    assert found.version == "263.7084.0"


def test_a_vs_code_build_is_not_a_standalone_archive():
    vsix = release("263.9000.0", "kotlin-server-0.0.30-mac-aarch64.vsix")
    assert newest([vsix]) is None


def test_no_release_gives_no_build():
    assert newest([]) is None


def test_a_document_that_is_no_list_gives_no_build():
    assert newest({"message": "API rate limit exceeded"}) is None


def test_a_release_without_notes_is_skipped():
    assert newest([{"tag_name": "kotlin-lsp/v1.0", "draft": False, "body": None}]) is None


def test_a_link_to_another_host_is_not_a_download():
    elsewhere = {
        "tag_name": "kotlin-lsp/v263.9000.0",
        "draft": False,
        "body": "[x](https://example.com/language-server/kotlin-server/263.9000.0/"
        "kotlin-server-263.9000.0-aarch64.sit) [y](https://example.com/language-server/"
        "kotlin-server/263.9000.0/kotlin-server-263.9000.0-aarch64.sit.sha256)",
    }
    assert newest([elsewhere]) is None


def test_the_build_names_its_file():
    found = newest([full_release("263.7084.0")])
    assert found is not None
    assert found.file_name == "kotlin-server-263.7084.0-aarch64.sit"


@pytest.mark.parametrize(
    "text",
    [
        f"{SHA} *kotlin-server-263.7084.0-aarch64.sit\n",
        f"{SHA}  kotlin-server-263.7084.0-aarch64.sit\n",
        f"{SHA.upper()} *kotlin-server-263.7084.0-aarch64.sit",
        f"{SHA}\n",
    ],
)
def test_the_checksum_file_gives_the_sha256(text):
    assert checksum_in(text, "kotlin-server-263.7084.0-aarch64.sit") == SHA


def test_a_checksum_of_another_file_is_refused():
    assert checksum_in(f"{SHA} *kotlin-server-263.7084.0.sit", "kotlin-server-x.sit") is None


@pytest.mark.parametrize("text", ["", "not a checksum", f"{SHA[:-1]} *a.sit", "<html>404</html>"])
def test_a_file_that_holds_no_sha256_gives_none(text):
    assert checksum_in(text, "a.sit") is None


LICENSE_HEAD = (
    "JETBRAINS FREE PLUGIN LICENSE AGREEMENT\n\n"
    "Version 1.0, effective as of September 15, 2025\n\nTHIS IS A LEGAL AGREEMENT.\n"
)


def test_the_license_of_the_release_is_the_one_cstudy_knows_when_its_name_matches():
    assert license_of(LICENSE_HEAD, KOTLIN_LSP_LICENSE) is KOTLIN_LSP_LICENSE


def test_a_new_version_of_the_agreement_is_another_license():
    changed = LICENSE_HEAD.replace("Version 1.0", "Version 2.0")
    found = license_of(changed, KOTLIN_LSP_LICENSE)
    assert found == License(
        KOTLIN_LSP_LICENSE.key,
        "JetBrains Free Plugin License Agreement 2.0",
        KOTLIN_LSP_LICENSE.url,
        KOTLIN_LSP_LICENSE.summary,
    )


def test_another_agreement_is_another_license_by_its_own_title():
    other = "JETBRAINS USER AGREEMENT\n\nVersion 3.1, effective as of January 1, 2027\n"
    found = license_of(other, KOTLIN_LSP_LICENSE)
    assert found is not None
    assert found.name == "JetBrains User Agreement 3.1"


@pytest.mark.parametrize("text", ["", "Apache License\n", "<!DOCTYPE html>\n<html>"])
def test_a_text_that_is_no_agreement_gives_none(text):
    assert license_of(text, KOTLIN_LSP_LICENSE) is None


STATUS = (
    "License: licensed\n"
    "Source: eap (Valid), licensed to kotlin-server EAP User, valid through 2026-11-12 "
    "(4 days left)\n"
    "This build does not require a license.\n"
)


def test_the_last_day_is_the_one_license_status_names():
    assert last_day(STATUS) == date(2026, 11, 12)


def test_a_status_without_a_last_day_gives_none():
    assert last_day("License: licensed\nSource: subscription\n") is None


def test_an_expired_build_says_so_at_start():
    expired = (
        "This build of kotlin-server has expired.\nThe IDE will now close.\n"
        "Please download a new build from https://github.com/kotlin/kotlin-lsp\n"
    )
    assert (expired_already(expired), expired_already(STATUS)) == (True, False)
