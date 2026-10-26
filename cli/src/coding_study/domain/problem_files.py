"""File names inside a problem directory (docs/specs/problem-format.md#directory-layout)."""

META_FILE = "meta.yaml"
TESTS_FILE = "tests.json"
PROBLEM_FILE = "problem.md"
GENERATOR_FILE = "generator.py"
CHECKER_FILE = "checker.py"
STRESS_CHECKER_FILE = "stress_checker.py"
RUBRIC_FILE = "rubric.md"
BUGGY_DIRECTORY = "buggy"
SOLUTIONS_DIRECTORY = "solutions"
EXPLANATION_NAME = "explanation.md"
EXPLANATION_FILE = f"{SOLUTIONS_DIRECTORY}/{EXPLANATION_NAME}"
BROKEN_DIRECTORY = f"{SOLUTIONS_DIRECTORY}/broken"
"""Concurrent problems: `<broken-id>.<ext>`, deliberately wrong references."""


def solution_file(file_name: str) -> str:
    """`solutions/<file_name>`, relative to the problem directory."""
    return f"{SOLUTIONS_DIRECTORY}/{file_name}"


def broken_file(file_name: str) -> str:
    """`solutions/broken/<file_name>`, relative to the problem directory."""
    return f"{BROKEN_DIRECTORY}/{file_name}"
