"""Python-only toolchains that really run code, for end-to-end command tests.

The real language adapters belong to the language streams; these stand-ins generate simple
Python stubs and run Python files through tests/fixtures/mini_python_runner.py with the real
`SubprocessRunner`.
"""

import shutil
import sys
from pathlib import Path

from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.application.environment import Environment
from coding_study.application.ports import (
    BuildScope,
    LanguageRunner,
    Prepared,
    PrepareResult,
    ProgressNotice,
    References,
    RunnerLaunch,
    StubGenerator,
)
from coding_study.domain import layout
from coding_study.domain.errors import LanguageNotSetUpError
from coding_study.domain.naming import member_name
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.signature import FunctionSignature, Param
from tests.fakes import make_environment

MINI_RUNNER = Path(__file__).resolve().parent / "fixtures" / "mini_python_runner.py"
HELLO_TIMEOUT_MS = 5_000


class SimplePythonStubGenerator:
    def generate(self, meta: ProblemMeta) -> str:
        signature = meta.signature
        if isinstance(signature, FunctionSignature):
            name = member_name(signature.name, Language.PYTHON)
            return f"def {name}({_params(signature.params)}):\n    raise NotImplementedError\n"
        lines = [f"class {signature.name}:"]
        constructor = _params(signature.constructor_params)
        lines += [f"    def __init__(self{_prefixed(constructor)}):", "        pass"]
        for method in signature.methods:
            parameters = _prefixed(_params(method.params))
            name = member_name(method.name, Language.PYTHON)
            lines += ["", f"    def {name}(self{parameters}):", "        raise NotImplementedError"]
        return "\n".join(lines) + "\n"


def _params(params: tuple[Param, ...]) -> str:
    return ", ".join(member_name(param.name, Language.PYTHON) for param in params)


def _prefixed(parameters: str) -> str:
    return f", {parameters}" if parameters else ""


class MiniPythonRunner:
    """`LanguageRunner` for Python: copies references into .cs/build like the real one."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def prepare(self, scope: BuildScope, notify: ProgressNotice) -> PrepareResult:
        if isinstance(scope, References):
            for source in scope.sources:
                path = layout.reference_build_path(scope.meta, source.approach_id, Language.PYTHON)
                destination = self._root / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source.path, destination)
        command = (sys.executable, str(MINI_RUNNER))
        return Prepared(RunnerLaunch(command, self._root, HELLO_TIMEOUT_MS))


class PythonOnlyToolchains:
    def __init__(self, root: Path) -> None:
        self._root = root

    def stub_generator(self, language: Language) -> StubGenerator:
        self._require_python(language, "stub generator")
        return SimplePythonStubGenerator()

    def runner(self, language: Language) -> LanguageRunner:
        self._require_python(language, "runner")
        return MiniPythonRunner(self._root)

    def _require_python(self, language: Language, component: str) -> None:
        if language is not Language.PYTHON:
            raise LanguageNotSetUpError(language, component)


def e2e_environment(root: Path, **overrides: object) -> Environment:
    parts: dict[str, object] = {
        "toolchains": PythonOnlyToolchains(root),
        "runner_process": SubprocessRunner(root / ".cs" / "runs"),
    }
    parts.update(overrides)
    return make_environment(root, **parts)
