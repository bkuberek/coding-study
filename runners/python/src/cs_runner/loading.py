"""Loads the target and finds its function or class (docs/specs/runners.md#locating-user-code).

A target is one file, or a project folder whose entry module defines the class
(docs/specs/runners.md#grading-job). Any failure is a TargetLoadError, which the runner reports
as the job's `load_error`.
"""

import importlib
import importlib.util
import inspect
import itertools
import sys
from collections.abc import Callable, Sequence
from importlib.abc import MetaPathFinder
from importlib.machinery import ModuleSpec, PathFinder, SourceFileLoader
from pathlib import Path, PurePath
from types import CodeType, ModuleType

from cs_runner.capture import capture_output
from cs_runner.failures import UserError, UserFile, describe
from cs_runner.request import ClassJob, Member, ProjectJob

MODULE_NAME_PREFIX = "cs_target_"
SYMBOL_NOT_FOUND = "SymbolNotFound"
_module_numbers = itertools.count(1)
_MISSING = object()


class TargetLoadError(Exception):
    def __init__(self, error: UserError) -> None:
        super().__init__(error.message)
        self.error = error


class _SourceOnlyLoader(SourceFileLoader):
    """Compiles from source on every load and never uses `__pycache__`: bytecode cached for an
    edit made within the same second, with the same size, would run the old code."""

    def get_code(self, fullname: str) -> CodeType:
        return self.source_to_code(self.get_data(self.path), self.path)


class _ProjectSourceFinder(MetaPathFinder):
    """Finds the modules whose files are under a project root, to load them from source."""

    def __init__(self, root: str) -> None:
        self._root = root

    def find_spec(
        self, fullname: str, path: Sequence[str] | None, target: ModuleType | None = None
    ) -> ModuleSpec | None:
        spec = PathFinder.find_spec(fullname, path)
        if spec is None or spec.origin is None or not isinstance(spec.loader, SourceFileLoader):
            return None
        if not PurePath(spec.origin).is_relative_to(self._root):
            return None
        spec.loader = _SourceOnlyLoader(fullname, spec.origin)
        return spec


def add_project_root(root: str) -> None:
    """Makes the modules under `root` importable after everything already on `sys.path`, so a
    project file named like a standard-library module never shadows it, and has each of them
    compile from source. The runner's own imports must come first."""
    if root in sys.path:
        return
    sys.path.append(root)
    sys.meta_path.insert(0, _ProjectSourceFinder(root))


def load_entry_class(job: ProjectJob) -> type:
    """Imports the entry module from the project folder and finds its class; anything the
    project prints while loading is discarded."""
    if not Path(job.root).is_dir():
        raise TargetLoadError(UserError("FileNotFoundError", f"no such folder: {job.root}"))
    add_project_root(job.root)
    try:
        with capture_output():
            module = importlib.import_module(job.module)
    except (Exception, SystemExit) as error:
        raise TargetLoadError(_import_failure(error, job)) from None
    symbol = job.constructor.symbol
    target = getattr(module, symbol, _MISSING)
    if target is _MISSING:
        raise TargetLoadError(UserError(SYMBOL_NOT_FOUND, f"{job.module} has no class {symbol}"))
    return _checked_class(target, job)


def _import_failure(error: BaseException, job: ProjectJob) -> UserError:
    """A missing entry module names what the project must define; any other failure is the
    project's own, with its trace."""
    if isinstance(error, ModuleNotFoundError) and _is_entry_or_parent(error.name, job.module):
        message = (
            f"the project has no module {job.module}; it must define class {job.constructor.symbol}"
        )
        return UserError(SYMBOL_NOT_FOUND, message)
    return describe(error, job.user_code)


def _is_entry_or_parent(name: str | None, module: str) -> bool:
    return name is not None and (module == name or module.startswith(f"{name}."))


def load_module(path: str) -> ModuleType:
    """Executes `path` as a new module; anything it prints is discarded."""
    if not Path(path).is_file():
        raise TargetLoadError(UserError("FileNotFoundError", f"no such file: {path}"))
    name = f"{MODULE_NAME_PREFIX}{next(_module_numbers)}"
    loader = _SourceOnlyLoader(name, path)
    spec = importlib.util.spec_from_file_location(name, path, loader=loader)
    if spec is None:
        raise TargetLoadError(UserError("ImportError", f"cannot import {path}"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        with capture_output():
            loader.exec_module(module)
    except (Exception, SystemExit) as error:
        del sys.modules[name]
        raise TargetLoadError(describe(error, UserFile(path))) from None
    return module


def find_function(module: ModuleType, function: Member) -> Callable[..., object]:
    target = _symbol(module, function.symbol, "function")
    if not callable(target):
        raise TargetLoadError(UserError("TypeError", f'"{function.symbol}" is not a function'))
    _check_arity(target, function, ())
    return target


def find_class(module: ModuleType, job: ClassJob) -> type:
    return _checked_class(_symbol(module, job.constructor.symbol, "class"), job)


def _checked_class(target: object, job: ClassJob | ProjectJob) -> type:
    """Fails unless `target` is a class with the declared constructor and methods."""
    constructor = job.constructor
    if not isinstance(target, type):
        raise TargetLoadError(UserError("TypeError", f'"{constructor.symbol}" is not a class'))
    _check_arity(target, constructor, ())
    for method in job.methods.values():
        _check_method(target, method)
    return target


def _symbol(module: ModuleType, symbol: str, kind: str) -> object:
    target = getattr(module, symbol, _MISSING)
    if target is _MISSING:
        message = f'{Path(module.__file__ or "").name} defines no {kind} "{symbol}"'
        raise TargetLoadError(UserError("AttributeError", message))
    return target


def _check_method(owner: type, method: Member) -> None:
    target = getattr(owner, method.symbol, _MISSING)
    if target is _MISSING or not callable(target):
        message = f'class "{owner.__name__}" has no method "{method.symbol}"'
        raise TargetLoadError(UserError("AttributeError", message))
    declared = inspect.getattr_static(owner, method.symbol)
    takes_instance = not isinstance(declared, staticmethod | classmethod)
    _check_arity(target, method, (None,) if takes_instance else ())


def _check_arity(
    target: Callable[..., object], member: Member, leading: tuple[object, ...]
) -> None:
    """Fails unless `target` accepts the declared parameters positionally after `leading`."""
    try:
        signature = inspect.signature(target)
    except (TypeError, ValueError):
        return
    try:
        signature.bind(*leading, *(None for _ in member.params))
    except TypeError as error:
        declared = ", ".join(param.name for param in member.params)
        message = f'"{member.symbol}" cannot take the declared parameters ({declared}): {error}'
        raise TargetLoadError(UserError("TypeError", message)) from None
