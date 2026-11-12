"""A problem's starter helpers: the file of `helpers/` that a language's generated starter ends
with (docs/specs/problem-format.md#starter-helpers)."""

import pytest

from coding_study.domain.problem import Language
from coding_study.domain.stub_helpers import (
    helper_file,
    helper_issues,
    helper_language,
    with_helper,
)


def test_the_helper_of_a_language_is_the_file_with_its_extension():
    names = ("sha256.rs", "tools.py")
    assert helper_file(Language.RUST, names) == "helpers/sha256.rs"
    assert helper_file(Language.PYTHON, names) == "helpers/tools.py"
    assert helper_file(Language.GO, names) is None


def test_a_kotlin_script_is_no_kotlin_helper():
    assert helper_file(Language.KOTLIN, ("build.kts",)) is None
    assert helper_language("build.kts") is None


@pytest.mark.parametrize(
    ("name", "language"),
    [
        ("a.py", Language.PYTHON),
        ("a.ts", Language.TYPESCRIPT),
        ("A.java", Language.JAVA),
        ("a.kt", Language.KOTLIN),
        ("a.go", Language.GO),
        ("a.rs", Language.RUST),
        ("README.md", None),
        ("rs", None),
    ],
)
def test_a_helper_names_its_language_by_its_extension(name, language):
    assert helper_language(name) is language


def test_the_helper_follows_the_stub_after_one_blank_line():
    stub = "pub struct Store {}\n"
    helper = "pub fn sha256() {}\n\n"
    assert with_helper(stub, helper, Language.RUST) == "pub struct Store {}\n\npub fn sha256() {}\n"


def test_a_python_helper_follows_after_two_blank_lines():
    assert with_helper("x = 1\n", "y = 2\n", Language.PYTHON) == "x = 1\n\n\ny = 2\n"


def test_a_stub_without_a_helper_is_unchanged():
    assert with_helper("x = 1\n", None, Language.PYTHON) == "x = 1\n"


def test_helpers_map_to_listed_languages_one_each():
    languages = (Language.PYTHON, Language.RUST)
    assert helper_issues(("a.rs", "b.py"), languages) == []
    assert helper_issues(("a.go", "notes.txt"), languages) == [
        ("helpers/a.go", "maps to no language in languages"),
        ("helpers/notes.txt", "maps to no language in languages"),
    ]
    assert helper_issues(("a.rs", "b.rs"), languages) == [
        ("helpers/b.rs", "a second helper for rust; a language has at most one"),
    ]
