"""`cstudy list` marks the languages the selected JDK cannot run, and its `--json` document holds
the range of each problem and the selected JDK (docs/specs/cli.md#cstudy-list)."""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from coding_study.domain.jdk import JdkSource
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import list_problems
from tests.fakes import FakeJdk, declare_jdk, jdk_of, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS, SCHEMAS_DIRECTORY

runner = CliRunner()
PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
WEB_API = json.loads((SCHEMAS_DIRECTORY / "web-api.schema.json").read_text())
TWO_SUM = "0001-two-sum"
LRU_CACHE = "0002-lru-cache"
ROW = "0001  two-sum           easy    arrays-hashing   new       -           "
LRU_ROW = "0002  lru-cache         medium  linked-list      new       -           "
SUPPORTS = "cstudy supports JDK 21 to 26"


def add_references(root: Path, directory: str, *names: str) -> None:
    for name in names:
        (root / "problems" / directory / "solutions" / name).write_text("// reference\n")


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """Two Sum with Python, Java and Kotlin references, and the LRU cache with Python's."""
    root = repository_root(tmp_path, PRACTICE)
    add_references(root, TWO_SUM, "hash-map.java", "hash-map.kt")
    return root


@pytest.fixture
def on_jdk(root: Path, monkeypatch: pytest.MonkeyPatch):
    def select(jdk: FakeJdk) -> None:
        environment = make_environment(root, jdk=jdk)
        monkeypatch.setattr(list_problems, "load_catalog_environment", lambda *_: environment)

    return select


def invoke(*arguments: str):
    return runner.invoke(cli.app, ["list", *arguments])


def document(*arguments: str):
    return json.loads(invoke("--json", *arguments).stdout)


def entry(slug: str, *arguments: str):
    return next(found for found in document(*arguments)["entries"] if found["slug"] == slug)


def valid(definition: str, value: Any) -> bool:
    schema = {"$ref": f"#/$defs/{definition}", "$defs": WEB_API["$defs"]}
    return not list(Draft202012Validator(schema).iter_errors(value))


# the marks


def test_a_jdk_in_range_marks_nothing_and_adds_no_footer(on_jdk):
    on_jdk(jdk_of(26))
    assert invoke().output.splitlines()[1:] == [ROW + "py java kt", LRU_ROW + "py"]


def test_a_jdk_above_the_range_marks_java_and_kotlin_with_one_footer(on_jdk):
    on_jdk(jdk_of(27))
    assert invoke().output.splitlines()[1:] == [
        ROW + "py java! kt!",
        LRU_ROW + "py",
        f"! java, kt: not run on JDK 27 (JAVA_HOME): {SUPPORTS}",
    ]


def test_a_jdk_below_the_range_is_marked_the_same_way(on_jdk):
    on_jdk(jdk_of(17))
    assert (
        invoke().output.splitlines()[-1] == f"! java, kt: not run on JDK 17 (JAVA_HOME): {SUPPORTS}"
    )


def test_the_footer_names_only_the_languages_it_marked(on_jdk, root):
    (root / "problems" / TWO_SUM / "solutions" / "hash-map.kt").unlink()
    on_jdk(jdk_of(27))
    assert invoke().output.splitlines()[-1].startswith("! java: not run on JDK 27")


def test_no_jdk_marks_java_and_kotlin_and_says_none_was_found(on_jdk):
    on_jdk(FakeJdk(None))
    assert invoke().output.splitlines()[1:] == [
        ROW + "py java! kt!",
        LRU_ROW + "py",
        "! java, kt: no JDK was found",
    ]


def test_a_java_home_without_a_jdk_is_named_in_the_footer(on_jdk):
    on_jdk(FakeJdk(None, java_home_without_jdk="/opt/jdk"))
    assert invoke().output.splitlines()[-1] == "! java, kt: JAVA_HOME (/opt/jdk) holds no JDK"


def test_a_problem_that_opts_in_to_the_jdk_is_not_marked_on_it(on_jdk, root):
    declare_jdk(root, TWO_SUM, "{max: 27}")
    on_jdk(jdk_of(27))
    assert invoke().output.splitlines()[1:] == [ROW + "py java kt", LRU_ROW + "py"]


def test_a_problem_whose_range_excludes_a_supported_jdk_is_marked_with_its_own_reason(on_jdk, root):
    declare_jdk(root, TWO_SUM, "{min: 24}")
    on_jdk(jdk_of(23))
    assert invoke().output.splitlines()[1:] == [
        ROW + "py java! kt!",
        LRU_ROW + "py",
        "! java, kt: not run on JDK 23 (JAVA_HOME): outside the JDK range the problem declares",
    ]


def test_the_language_filter_still_filters_by_reference_language(on_jdk):
    on_jdk(jdk_of(27))
    assert invoke("--lang", "java").output.splitlines()[1:] == [
        ROW + "py java! kt!",
        f"! java, kt: not run on JDK 27 (JAVA_HOME): {SUPPORTS}",
    ]


def test_a_listing_without_a_marked_language_has_no_footer(on_jdk):
    on_jdk(jdk_of(27))
    assert invoke("--difficulty", "medium").output.splitlines()[1:] == [LRU_ROW + "py"]


# `--json`


def test_each_problem_has_its_effective_range(on_jdk):
    on_jdk(jdk_of(26))
    assert entry("two-sum")["jdk"] == {"min": 21, "max": 26}


def test_a_declared_bound_is_in_the_range(on_jdk, root):
    declare_jdk(root, TWO_SUM, "{min: 24}")
    on_jdk(jdk_of(26))
    assert entry("two-sum")["jdk"] == {"min": 24, "max": 26}


def test_a_problem_without_java_and_kotlin_has_no_range(on_jdk, root):
    meta = root / "problems" / LRU_CACHE / "meta.yaml"
    meta.write_text(f"{meta.read_text()}languages: [python, typescript, go, rust]\n")
    on_jdk(jdk_of(26))
    assert entry("lru-cache")["jdk"] is None


def test_an_item_has_no_range(on_jdk, root):
    shutil.copytree(FIXTURE_TRACKS, root / "tracks")
    on_jdk(jdk_of(26))
    assert entry("url-shortener")["jdk"] is None


def test_the_document_holds_the_selected_jdk(on_jdk):
    on_jdk(jdk_of(26))
    assert document()["selected_jdk"] == {
        "version": "26.0.1",
        "feature": 26,
        "source": "JAVA_HOME",
        "supported": True,
    }


def test_a_jdk_above_the_range_is_not_supported(on_jdk):
    on_jdk(jdk_of(27))
    assert document()["selected_jdk"]["supported"] is False


def test_the_source_can_be_the_path(on_jdk):
    on_jdk(jdk_of(21, JdkSource.PATH))
    assert document()["selected_jdk"]["source"] == "PATH"


@pytest.mark.parametrize(
    "jdk",
    [FakeJdk(None), FakeJdk(None, java_home_without_jdk="/opt/jdk")],
    ids=["none", "a JAVA_HOME without a JDK"],
)
def test_no_jdk_is_null(on_jdk, jdk):
    on_jdk(jdk)
    assert document()["selected_jdk"] is None


def test_the_fields_match_the_schema(on_jdk):
    on_jdk(jdk_of(26))
    found = document()
    assert valid("selected_jdk", found["selected_jdk"])
    assert all(valid("jdk_range", e["jdk"]) for e in found["entries"])


def test_a_missing_jdk_matches_the_schema(on_jdk):
    on_jdk(FakeJdk(None))
    assert valid("selected_jdk", document()["selected_jdk"])
