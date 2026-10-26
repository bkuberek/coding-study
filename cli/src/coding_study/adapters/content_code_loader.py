"""Loads content code (generator.py, checker.py, stress_checker.py) in-process (architecture.md).

Content code is stdlib-only Python from the repository's own problems; every failure in it is a
content error naming the file.
"""

import hashlib
import json
import random
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any, cast

from coding_study.domain.cases import JsonValue
from coding_study.domain.comparators import Checker
from coding_study.domain.errors import ContentError, ContentIssue
from coding_study.domain.invariants import StressChecker

GENERATE_FUNCTION = "generate"
VALIDATE_FUNCTION = "validate"
CHECK_FUNCTION = "check"
REJECTED_WITHOUT_MESSAGE = "validate() rejected the input"


class ContentCodeLoader:
    """`ContentCode`; `root` only shortens file names in reported issues."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def generator(self, path: Path) -> "ModuleGenerator":
        module = self._load(path)
        function = self._function(module, GENERATE_FUNCTION, path)
        return ModuleGenerator(
            function, getattr(module, VALIDATE_FUNCTION, None), self._source(path)
        )

    def checker(self, path: Path) -> Checker:
        check = self._function(self._load(path), CHECK_FUNCTION, path)

        def checker(
            case_input: dict[str, JsonValue], output: JsonValue, expected: JsonValue | None
        ) -> str | None:
            reason = check(case_input, output, expected)
            return None if reason is None else str(reason)

        return checker

    def stress_checker(self, path: Path) -> StressChecker:
        check = self._function(self._load(path), CHECK_FUNCTION, path)

        def checker(
            name: str, scenario: dict[str, JsonValue], run: dict[str, JsonValue]
        ) -> str | None:
            reason = check(name, scenario, run)
            return None if reason is None else str(reason)

        return checker

    def _load(self, path: Path) -> ModuleType:
        """Compile and run the source directly, so no `__pycache__` lands in problems/."""
        name = f"cs_content_{hashlib.sha256(str(path).encode()).hexdigest()[:16]}"
        module = ModuleType(name)
        module.__file__ = str(path)
        sys.modules[name] = module  # dataclasses and pickling look modules up by name
        try:
            exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
        except Exception as error:  # content code: report any failure as a content error
            del sys.modules[name]
            raise _content_error(
                self._source(path), f"cannot be loaded: {_describe(error)}"
            ) from error
        return module

    def _function(self, module: ModuleType, name: str, path: Path) -> Any:
        function = getattr(module, name, None)
        if not callable(function):
            raise _content_error(self._source(path), f"no {name}() function")
        return function

    def _source(self, path: Path) -> str:
        return (
            path.relative_to(self._root).as_posix()
            if path.is_relative_to(self._root)
            else str(path)
        )


class ModuleGenerator:
    """`InputGenerator` over a loaded generator.py."""

    def __init__(self, generate: Any, validate: Any, source: str) -> None:
        self._generate = generate
        self._validate = validate
        self._source = source

    def generate(self, n: int, seed: int) -> dict[str, JsonValue]:
        call = f"generate(n={n}, seed={seed})"
        try:
            value: object = self._generate(random.Random(seed), n)
        except Exception as error:  # content code: report any failure as a content error
            raise _content_error(self._source, f"{call} raised {_describe(error)}") from error
        if not isinstance(value, dict):
            raise _content_error(self._source, f"{call} must return a JSON object (a dict)")
        return self._canonical(cast(object, value), call)

    def validate(self, case_input: Mapping[str, JsonValue]) -> str | None:
        if self._validate is None:
            return None
        try:
            self._validate(dict(case_input))
        except AssertionError as error:
            return str(error) or REJECTED_WITHOUT_MESSAGE
        except Exception as error:  # content code: report any failure as a content error
            raise _content_error(self._source, f"validate() raised {_describe(error)}") from error
        return None

    def _canonical(self, value: object, call: str) -> dict[str, JsonValue]:
        try:
            return json.loads(json.dumps(value, allow_nan=False))
        except (TypeError, ValueError) as error:
            raise _content_error(
                self._source, f"{call} returned a value that is not JSON: {error}"
            ) from error


def _describe(error: Exception) -> str:
    return f"{type(error).__name__}: {error}"


def _content_error(source: str, message: str) -> ContentError:
    return ContentError([ContentIssue(source, "", message)])
