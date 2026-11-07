"""`sets.yaml` on disk: read, refused when wrong and changed by the lines a change needs
(docs/decisions/0023-problem-sets.md#what-a-write-keeps)."""

import json
from collections import Counter
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from coding_study.adapters.workspace_fs import WorkspaceFs
from coding_study.adapters.yaml_problem_sets import YamlProblemSets
from coding_study.domain.errors import ConfigError
from coding_study.domain.problem_sets import ProblemSet
from tests.helpers import SCHEMAS_DIRECTORY

HAND_WRITTEN = """\
# My sets, kept by hand.

sets:
  # For the loop on the 12th.
  backend-loop:
    # Say why each is here.
    description: "The backend loop"   # the date moves
    problems:
      # warm up
      - two-sum    # again, faster
      - lru-cache

      # the hard one
      - 'url-shortener'
      # keep going

  # After that.
  data-loop:
    problems: []
# The end.
"""
STORE_SCHEMA = json.loads((SCHEMAS_DIRECTORY / "sets.schema.json").read_text())


@pytest.fixture
def file(tmp_path: Path) -> Path:
    return tmp_path / "sets.yaml"


@pytest.fixture
def store(tmp_path: Path) -> YamlProblemSets:
    return YamlProblemSets(WorkspaceFs(tmp_path))


@pytest.fixture
def written(file: Path, store: YamlProblemSets) -> YamlProblemSets:
    file.write_text(HAND_WRITTEN)
    return store


def lines_gone_and_new(before: str, after: str) -> tuple[list[str], list[str]]:
    old, new = Counter(before.splitlines()), Counter(after.splitlines())
    return sorted((old - new).elements()), sorted((new - old).elements())


def test_no_file_is_no_sets(store):
    assert store.read() == ()


def test_a_file_of_comments_is_no_sets(file, store):
    file.write_text("# nothing yet\n")
    assert store.read() == ()


def test_reading_the_hand_written_file(written):
    assert written.read() == (
        ProblemSet("backend-loop", "The backend loop", ("two-sum", "lru-cache", "url-shortener")),
        ProblemSet("data-loop"),
    )


def test_reading_makes_no_file(file, store):
    store.read()
    assert not file.exists()


@pytest.mark.parametrize(
    ("text", "named"),
    [
        ("sets:\n  loop: [unclosed\n", "line 3"),
        ("sets:\n\tloop: {}\n", "line 2"),
        ("- a\n- b\n", "a mapping"),
        ("sets:\n  Bad Name: {}\n", '"Bad Name"'),
        ("sets:\n  loop: {}\n  loop: {}\n", "twice"),
        ("sets: {}\n---\nsets: {}\n", "single document"),
        ("sets:\n  on: {}\n", "quote"),
    ],
)
def test_a_file_that_is_wrong_is_refused_saying_why(file, store, text, named):
    file.write_text(text)
    with pytest.raises(ConfigError, match=named):
        store.read()


def test_a_directory_in_its_place_is_refused(file, store):
    file.mkdir()
    with pytest.raises(ConfigError, match="can't be read"):
        store.read()


def test_a_file_that_is_not_text_is_refused(file, store):
    file.write_bytes(b"\xff\xfe\x00bad")
    with pytest.raises(ConfigError, match="UTF-8"):
        store.read()


@pytest.mark.parametrize(
    "change",
    [
        lambda store: store.add(ProblemSet("new-set")),
        lambda store: store.set_problems("loop", ("a",)),
        lambda store: store.rename("loop", "other"),
        lambda store: store.delete("loop"),
    ],
)
def test_a_file_that_does_not_parse_is_never_overwritten(file, store, change):
    text = "sets:\n  loop: [unclosed\n"
    file.write_text(text)
    with pytest.raises(ConfigError):
        change(store)
    assert file.read_text() == text


def test_the_first_write_makes_the_file_and_says_what_it_is(file, store):
    store.add(ProblemSet("backend-loop", "On the 12th", ("two-sum",)))
    assert file.read_text() == (
        "# Your problem sets: edit by hand, or with cstudy set. "
        "The order is the order you study in.\n"
        "sets:\n"
        "  backend-loop:\n"
        "    description: On the 12th\n"
        "    problems:\n"
        "      - two-sum\n"
    )


def test_a_new_empty_set_reads_back(store):
    store.add(ProblemSet("backend-loop"))
    assert store.read() == (ProblemSet("backend-loop"),)


def test_a_name_yaml_would_read_as_a_boolean_is_quoted(store):
    store.add(ProblemSet("on", None, ("no",)))
    assert store.read() == (ProblemSet("on", None, ("no",)),)


def test_a_description_that_looks_like_yaml_reads_back(store):
    store.add(ProblemSet("loop", "12: the #1 loop, 'really'"))
    assert store.read()[0].description == "12: the #1 loop, 'really'"


def test_adding_a_set_changes_no_line_of_the_file(file, written):
    written.add(ProblemSet("new-set"))
    gone, new = lines_gone_and_new(HAND_WRITTEN, file.read_text())
    assert (gone, new) == ([], ["", "    problems: []", "  new-set:"])


def test_a_new_set_follows_the_last_one(written):
    written.add(ProblemSet("new-set"))
    assert [problem_set.name for problem_set in written.read()] == [
        "backend-loop",
        "data-loop",
        "new-set",
    ]


def test_a_comment_after_the_last_set_stays_at_the_end(file, written):
    written.add(ProblemSet("new-set"))
    assert file.read_text().endswith("# The end.\n")


def test_adding_a_set_to_a_file_with_an_empty_sets_key(file, store):
    file.write_text("# Top.\nsets:\n")
    store.add(ProblemSet("loop", None, ("a",)))
    assert (store.read(), file.read_text().startswith("# Top.\nsets:\n  loop:\n")) == (
        (ProblemSet("loop", None, ("a",)),),
        True,
    )


def test_adding_a_set_to_a_file_with_an_empty_flow_mapping(file, store):
    file.write_text("sets: {}  # none yet\n")
    store.add(ProblemSet("loop"))
    assert (store.read(), file.read_text().startswith("sets:  # none yet\n")) == (
        (ProblemSet("loop"),),
        True,
    )


def test_adding_a_set_keeps_another_indent(file, store):
    file.write_text("sets:\n    first:\n        problems: []\n")
    store.add(ProblemSet("second"))
    assert "\n    second:\n" in file.read_text()


def test_adding_a_slug_adds_one_line_with_the_indent_of_the_others(file, written):
    written.set_problems("backend-loop", ("two-sum", "lru-cache", "url-shortener", "new-one"))
    gone, new = lines_gone_and_new(HAND_WRITTEN, file.read_text())
    assert (gone, new) == ([], ["      - new-one"])


def test_a_new_slug_goes_after_the_last_and_before_the_comment_that_trails(file, written):
    written.set_problems("backend-loop", ("two-sum", "lru-cache", "url-shortener", "new-one"))
    assert "- 'url-shortener'\n      - new-one\n      # keep going\n" in file.read_text()


def test_removing_a_slug_takes_only_its_line_and_the_comment_above_it(file, written):
    written.set_problems("backend-loop", ("two-sum", "lru-cache"))
    gone, new = lines_gone_and_new(HAND_WRITTEN, file.read_text())
    assert (gone, new) == (["", "      # the hard one", "      - 'url-shortener'"], [])


def test_moving_a_slug_carries_its_comments_and_changes_no_line(file, written):
    written.set_problems("backend-loop", ("lru-cache", "two-sum", "url-shortener"))
    text = file.read_text()
    assert (
        lines_gone_and_new(HAND_WRITTEN, text),
        text.index("- lru-cache") < text.index("# warm up") < text.index("- two-sum    # again"),
    ) == (([], []), True)


def test_a_slug_that_was_quoted_stays_quoted_when_another_moves(file, written):
    written.set_problems("backend-loop", ("url-shortener", "two-sum", "lru-cache"))
    assert "- 'url-shortener'" in file.read_text()


def test_the_problems_read_back_in_the_new_order(written):
    order = ("url-shortener", "lru-cache", "two-sum")
    written.set_problems("backend-loop", order)
    assert written.read()[0].slugs == order


def test_the_first_slug_of_an_empty_flow_list_makes_a_block_list(file, written):
    written.set_problems("data-loop", ("two-sum",))
    assert "    problems:\n      - two-sum\n# The end.\n" in file.read_text()


def test_removing_the_last_slug_leaves_an_empty_set(written):
    written.set_problems("backend-loop", ())
    assert written.read()[0].slugs == ()


def test_a_slug_comes_back_after_the_list_was_emptied(written):
    written.set_problems("backend-loop", ())
    written.set_problems("backend-loop", ("two-sum",))
    assert written.read()[0].slugs == ("two-sum",)


def test_a_flow_list_becomes_a_block_list_and_keeps_the_comment_on_its_line(file, store):
    file.write_text("sets:\n  loop:\n    problems: [a, b]  # short\n")
    store.set_problems("loop", ("a", "b", "c"))
    assert file.read_text() == (
        "sets:\n  loop:\n    problems:  # short\n      - a\n      - b\n      - c\n"
    )


def test_a_list_at_the_indent_of_its_key_keeps_that_indent(file, store):
    file.write_text("sets:\n  loop:\n    problems:\n    - a\n    - b\n")
    store.set_problems("loop", ("a", "b", "c"))
    assert "\n    - b\n    - c\n" in file.read_text()


def test_a_set_with_no_problems_key_is_written_again_when_it_changes(file, store):
    file.write_text("sets:\n  # Above.\n  loop:\n    description: x\n")
    store.set_problems("loop", ("a",))
    assert file.read_text() == (
        "sets:\n  # Above.\n  loop:\n    description: x\n    problems:\n      - a\n"
    )


def test_a_set_in_flow_style_is_written_again_when_it_changes(file, store):
    file.write_text("sets:\n  loop: {description: x, problems: [a]}\n  other: {}\n")
    store.set_problems("loop", ("a", "b"))
    assert store.read() == (ProblemSet("loop", "x", ("a", "b")), ProblemSet("other"))


def test_sets_in_flow_style_are_kept_when_another_is_added(file, store):
    file.write_text("sets: {loop: {problems: [a]}}\n")
    store.add(ProblemSet("other"))
    assert store.read() == (ProblemSet("loop", None, ("a",)), ProblemSet("other"))


def test_renaming_changes_only_the_name(file, written):
    written.rename("backend-loop", "platform-loop")
    gone, new = lines_gone_and_new(HAND_WRITTEN, file.read_text())
    assert (gone, new) == (["  backend-loop:"], ["  platform-loop:"])


def test_renaming_keeps_the_rows(written):
    written.rename("backend-loop", "platform-loop")
    assert written.read()[0] == ProblemSet(
        "platform-loop", "The backend loop", ("two-sum", "lru-cache", "url-shortener")
    )


def test_deleting_a_set_takes_its_lines_and_the_comment_above_it(file, written):
    written.delete("backend-loop")
    assert file.read_text() == (
        "# My sets, kept by hand.\n\nsets:\n  # After that.\n  data-loop:\n"
        "    problems: []\n# The end.\n"
    )


def test_deleting_the_last_set_leaves_the_comment_after_it(file, written):
    written.delete("data-loop")
    assert file.read_text().endswith("      # keep going\n# The end.\n")


def test_deleting_every_set_leaves_a_file_with_no_sets(written):
    written.delete("data-loop")
    written.delete("backend-loop")
    assert written.read() == ()


def test_a_set_comes_back_after_every_set_was_deleted(written):
    written.delete("data-loop")
    written.delete("backend-loop")
    written.add(ProblemSet("again"))
    assert written.read() == (ProblemSet("again"),)


def test_a_list_an_alias_shares_is_refused_and_the_file_kept(file, store):
    text = "sets:\n  one:\n    problems: &shared\n      - a\n  two:\n    problems: *shared\n"
    file.write_text(text)
    with pytest.raises(ConfigError, match="edit the file by hand"):
        store.set_problems("two", ("a", "b"))
    assert file.read_text() == text


def test_a_file_with_an_alias_still_reads(file, store):
    file.write_text(
        "sets:\n  one:\n    problems: &shared\n      - a\n  two:\n    problems: *shared\n"
    )
    assert store.read()[1].slugs == ("a",)


def test_the_file_keeps_its_mode(file, written):
    file.chmod(0o640)
    written.add(ProblemSet("new-set"))
    assert file.stat().st_mode & 0o777 == 0o640


def test_a_write_leaves_no_other_file(tmp_path, written):
    written.add(ProblemSet("new-set"))
    assert [path.name for path in tmp_path.iterdir()] == ["sets.yaml"]


def test_a_link_is_read(tmp_path, file, store):
    real = tmp_path / "elsewhere.yaml"
    real.write_text("sets:\n  loop: {}\n")
    file.symlink_to(real)
    assert store.read() == (ProblemSet("loop"),)


def test_a_link_is_not_written_through(tmp_path, file, store):
    real = tmp_path / "elsewhere.yaml"
    real.write_text("sets:\n  loop: {}\n")
    file.symlink_to(real)
    with pytest.raises(ConfigError, match="symbolic link"):
        store.add(ProblemSet("other"))
    assert (real.read_text(), file.is_symlink()) == ("sets:\n  loop: {}\n", True)


def test_a_file_without_a_last_newline_takes_a_change(file, store):
    file.write_text("sets:\n  loop:\n    problems:\n      - a")
    store.set_problems("loop", ("a", "b"))
    assert store.read()[0].slugs == ("a", "b")


def test_a_file_with_windows_line_ends_takes_a_change(file, store):
    file.write_bytes(b"sets:\r\n  loop:\r\n    problems:\r\n      - a\r\n")
    store.set_problems("loop", ("a", "b"))
    assert store.read()[0].slugs == ("a", "b")


@pytest.mark.parametrize(
    "document",
    [
        {},
        {"sets": None},
        {"sets": {}},
        {"sets": {"backend-loop": None}},
        {"sets": {"backend-loop": {"description": "x", "problems": ["two-sum", "lru-cache"]}}},
    ],
)
def test_the_schema_takes_what_the_store_takes(document):
    Draft202012Validator(STORE_SCHEMA).validate(document)


@pytest.mark.parametrize(
    "document",
    [
        {"set": {}},
        {"sets": []},
        {"sets": {"Bad Name": {}}},
        {"sets": {"loop": {"problem": []}}},
        {"sets": {"loop": {"problems": "two-sum"}}},
        {"sets": {"loop": {"problems": [1]}}},
        {"sets": {"loop": {"problems": ["a", "a"]}}},
        {"sets": {"loop": {"description": 1}}},
    ],
)
def test_the_schema_refuses_what_the_store_refuses(document):
    assert not Draft202012Validator(STORE_SCHEMA).is_valid(document)


def test_the_schema_is_a_schema():
    Draft202012Validator.check_schema(STORE_SCHEMA)
