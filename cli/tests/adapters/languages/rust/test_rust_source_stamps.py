"""Cargo rebuilds a crate when a source is newer than the last build, so a source replaced by a
copy that keeps an older time (`rsync -a`, `cp -p`) must be touched before Cargo looks."""

import os
import time
from pathlib import Path

import pytest

from coding_study.adapters.languages.rust.source_stamps import (
    project_sources,
    touch_replaced_sources,
)

AN_HOUR = 3600
LONG_AGO = time.time() - 24 * AN_HOUR


@pytest.fixture
def record(tmp_path: Path) -> Path:
    return tmp_path / "build" / "sources.json"


def source(directory: Path, name: str, text: str = "fn main() {}\n") -> Path:
    """A file whose modification time is long ago."""
    path = directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    os.utime(path, (LONG_AGO, LONG_AGO))
    return path


def replace_keeping_the_time(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    os.utime(path, (LONG_AGO, LONG_AGO))


def mtime(path: Path) -> float:
    return path.stat().st_mtime


def test_the_first_build_touches_nothing(tmp_path, record):
    lib = source(tmp_path, "lib.rs")
    touch_replaced_sources([lib], record)
    assert mtime(lib) == LONG_AGO


def test_a_source_replaced_by_an_older_copy_is_touched(tmp_path, record):
    lib = source(tmp_path, "lib.rs")
    touch_replaced_sources([lib], record)
    replace_keeping_the_time(lib, "fn main() { changed(); }\n")
    touch_replaced_sources([lib], record)
    assert mtime(lib) > time.time() - AN_HOUR


def test_a_source_that_did_not_change_keeps_its_time(tmp_path, record):
    lib = source(tmp_path, "lib.rs")
    touch_replaced_sources([lib], record)
    touch_replaced_sources([lib], record)
    assert mtime(lib) == LONG_AGO


def test_only_the_replaced_source_is_touched(tmp_path, record):
    lib, other = source(tmp_path, "lib.rs"), source(tmp_path, "other.rs")
    touch_replaced_sources([lib, other], record)
    replace_keeping_the_time(lib, "fn main() { changed(); }\n")
    touch_replaced_sources([lib, other], record)
    assert mtime(other) == LONG_AGO


def test_a_touched_source_is_not_touched_again_at_the_next_build(tmp_path, record):
    lib = source(tmp_path, "lib.rs")
    touch_replaced_sources([lib], record)
    replace_keeping_the_time(lib, "fn main() { changed(); }\n")
    touch_replaced_sources([lib], record)
    replace_keeping_the_time(lib, "fn main() { changed(); }\n")
    touch_replaced_sources([lib], record)
    assert mtime(lib) == LONG_AGO


def test_a_source_that_came_after_the_last_build_is_touched(tmp_path, record):
    lib = source(tmp_path, "lib.rs")
    touch_replaced_sources([lib], record)
    added = source(tmp_path, "added.rs")
    touch_replaced_sources([lib, added], record)
    assert mtime(added) > time.time() - AN_HOUR


def test_a_source_that_is_gone_is_no_error(tmp_path, record):
    lib = source(tmp_path, "lib.rs")
    touch_replaced_sources([lib], record)
    lib.unlink()
    touch_replaced_sources([lib], record)


@pytest.mark.parametrize("damage", ["", "not json", "[1, 2]", '{"x": 3}'])
def test_a_record_that_cannot_be_read_counts_as_a_first_build(tmp_path, record, damage):
    lib = source(tmp_path, "lib.rs")
    record.parent.mkdir(parents=True)
    record.write_text(damage, encoding="utf-8")
    touch_replaced_sources([lib], record)
    assert mtime(lib) == LONG_AGO


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads every file")
def test_a_source_that_cannot_be_read_is_no_error(tmp_path, record):
    lib = source(tmp_path, "lib.rs")
    touch_replaced_sources([lib], record)
    lib.chmod(0)
    try:
        touch_replaced_sources([lib], record)
    finally:
        lib.chmod(0o600)


def test_the_sources_of_a_project_are_its_rust_files_and_manifests(tmp_path):
    for name in ("Cargo.toml", "Cargo.lock", "src/lib.rs", "tests/level_1.rs", "build.rs"):
        source(tmp_path, name)
    source(tmp_path, "README.md")
    assert sorted(path.relative_to(tmp_path).as_posix() for path in project_sources(tmp_path)) == [
        "Cargo.lock",
        "Cargo.toml",
        "build.rs",
        "src/lib.rs",
        "tests/level_1.rs",
    ]


def test_a_projects_build_output_and_hidden_folders_are_not_its_sources(tmp_path):
    source(tmp_path, "src/lib.rs")
    source(tmp_path, "target/debug/build/out.rs")
    source(tmp_path, ".git/hooks/pre-commit.rs")
    assert [path.name for path in project_sources(tmp_path)] == ["lib.rs"]
