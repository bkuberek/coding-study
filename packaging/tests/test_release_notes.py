import pytest
from release_notes import main, release_notes

CHANGELOG = """# CHANGELOG

<!-- version list -->

## v0.4.10 (2026-11-02)

### Features

- **cli**: Ten

## v0.4.1 (2026-11-01)

### Bug Fixes

- **cli**: One

## v0.4.0 (2026-10-29)

### Features

- **problems**: Zero
"""


def test_section_ends_at_the_next_release():
    assert release_notes(CHANGELOG, "v0.4.1") == "### Bug Fixes\n\n- **cli**: One\n"


def test_last_section_runs_to_the_end():
    assert release_notes(CHANGELOG, "v0.4.0") == "### Features\n\n- **problems**: Zero\n"


def test_tag_is_not_matched_as_a_prefix():
    assert "One" not in release_notes(CHANGELOG, "v0.4.10")


def test_heading_without_a_date_matches():
    assert release_notes("## v1.0.0\n\nNotes\n", "v1.0.0") == "Notes\n"


def test_missing_release_raises():
    with pytest.raises(LookupError, match=r"no section for v9\.9\.9"):
        release_notes(CHANGELOG, "v9.9.9")


def test_main_prints_the_section(tmp_path, capsys):
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(CHANGELOG, encoding="utf-8")
    main([str(changelog), "v0.4.0"])
    assert capsys.readouterr().out == "### Features\n\n- **problems**: Zero\n"


def test_main_exits_when_the_release_is_missing(tmp_path):
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(CHANGELOG, encoding="utf-8")
    with pytest.raises(SystemExit, match=r"no section for v9\.9\.9"):
        main([str(changelog), "v9.9.9"])
