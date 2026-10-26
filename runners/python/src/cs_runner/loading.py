"""Loads the target file and finds its function or class (docs/specs/runners.md#locating-user-code).

Any failure is a TargetLoadError, which the runner reports as the job's `load_error`.
"""

import importlib.util
import inspect
import itertools
import sys
from collections.abc import Callable
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import CodeType, ModuleType

from cs_runner.capture import capture_output
from cs_runner.failures import UserError, describe
from cs_runner.request import ClassJob, Member

MODULE_NAME_PREFIX = "cs_target_"
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
        raise TargetLoadError(describe(error, path)) from None
    return module


def find_function(module: ModuleType, function: Member) -> Callable[..., object]:
    target = _symbol(module, function.symbol, "function")
    if not callable(target):
        raise TargetLoadError(UserError("TypeError", f'"{function.symbol}" is not a function'))
    _check_arity(target, function, ())
    return target


def find_class(module: ModuleType, job: ClassJob) -> type:
    constructor = job.constructor
    target = _symbol(module, constructor.symbol, "class")
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
