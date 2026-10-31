import json
import shutil
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import yaml

from coding_study.adapters.conformance_fixtures import (
    conformance_repository,
    load_conformance_suite,
)
from coding_study.domain.conformance import ConformanceSuite
from coding_study.domain.problem import ProblemKind

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIRECTORY = REPOSITORY_ROOT / "schemas"
CATALOG_PROBLEMS = REPOSITORY_ROOT / "problems"
FIRST_CATALOG = ("0001-two-sum", "0002-lru-cache", "0003-invert-binary-tree")
"""A fixed slice of the real catalog, for tests that pick among problems: content added later
must not change their picks."""
FIXTURE_PROBLEMS = Path(__file__).resolve().parent / "fixtures" / "problems"
WORKSPACE_TEMPLATE = (
    REPOSITORY_ROOT / "cli" / "src" / "coding_study" / "adapters" / "workspace_template"
)
"""What `cstudy init` copies into a new workspace."""
FIXTURE_TRACKS = Path(__file__).resolve().parent / "fixtures" / "tracks"
"""Non-autograded fixture items: tracks/<track>/<slug>/."""
CONCURRENCY_PROBLEMS = Path(__file__).resolve().parent / "fixtures" / "concurrency" / "problems"
"""A concurrent fixture problem with correct and broken references in every language."""
PROJECT_PROBLEMS = Path(__file__).resolve().parent / "fixtures" / "project" / "problems"
"""A Python project fixture problem: a starter tree and a reference overlay."""
BANK_PROJECT = "0001-bank-project-python"
FAKE_RUNNER_PROGRAM = (
    f'#!/bin/sh\nexec "{sys.executable}" "{Path(__file__).resolve().parent}'
    '/fixtures/fake_runner.py" "$@"\n'
)
"""The text of an executable that stands in for a compiled runner binary: it answers the runner
protocol like fixtures/fake_runner.py."""
RUNNER_TRUNCATION_NOTICE = "\n[output truncated at 4 KiB]\n"
"""What every runner appends to captured output over 4 KiB (docs/specs/runners.md)."""


def sequential_conformance_suite() -> ConformanceSuite:
    """The conformance expectations of fixtures without stress cases.

    The per-language end-to-end tests replay those case by case; the stress fixtures (Phase 5)
    run through `cstudy verify --conformance` (tests/adapters/languages/test_stress_conformance.py).
    """
    suite = load_conformance_suite(REPOSITORY_ROOT)
    fixtures = conformance_repository(REPOSITORY_ROOT)
    expectations = tuple(
        expectation
        for expectation in suite.expectations
        if fixtures.load(expectation.slug).meta.kind is not ProblemKind.CONCURRENT
    )
    return replace(suite, expectations=expectations)


def copy_catalog_problems(destination: Path, directory_names: tuple[str, ...]) -> Path:
    """`destination` holding copies of the named problem directories of the real catalog."""
    for name in directory_names:
        shutil.copytree(CATALOG_PROBLEMS / name, destination / name)
    return destination


def load_fixture_meta(directory_name: str, problems: Path = FIXTURE_PROBLEMS) -> dict[str, Any]:
    return yaml.safe_load((problems / directory_name / "meta.yaml").read_text())


def load_fixture_tests(directory_name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_PROBLEMS / directory_name / "tests.json").read_text())


MAPPING_TABLE_TYPES = frozenset(
    {
        *("int", "long", "double", "bool", "string", "char"),
        *("int[]", "long[]", "double[]", "bool[]", "char[]", "string[]"),
        *("int[][]", "long[][]", "double[][]", "bool[][]", "char[][]", "string[][]"),
        *("list<int>", "list<long>", "list<double>", "list<bool>", "list<char>", "list<string>"),
        *("list<int[]>", "list<list<int>>", "list<list<string>>"),
        *("ListNode", "TreeNode", "GraphNode", "ListNode[]", "list<TreeNode>"),
        *("decimal", "date", "decimal[]", "date[]", "decimal[][]", "date[][]"),
        *("list<decimal>", "list<date>"),
    }
)
"""Every value type row of the mapping table in docs/specs/problem-format.md#type-mapping."""


def mark_workspace(directory: Path, created_with: str = "0.1.0") -> Path:
    """`directory` as a workspace: it holds the marker (installation-and-workspaces.md)."""
    marker = directory / ".cs" / "workspace.toml"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(f'schema = 1\ncreated_with = "{created_with}"\n')
    return directory
