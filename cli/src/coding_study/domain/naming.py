"""Per-language symbol names (docs/specs/problem-format.md#naming-rules).

Canonical names are lowerCamelCase (classes PascalCase). Python and Rust convert functions,
methods and parameters to snake_case; TypeScript, Java, Kotlin and Go keep the canonical names.
Runners never convert names: the CLI sends them in the request
(docs/specs/runners.md#request-file).
"""

import builtins
import keyword
import re
from collections.abc import Iterable, Iterator, Mapping, Set
from dataclasses import dataclass
from typing import assert_never

from coding_study.domain.problem import Language
from coding_study.domain.signature import (
    ClassSignature,
    FunctionSignature,
    Param,
    Signature,
    declared_types,
)
from coding_study.domain.type_dsl import Scalar, scalars_of

_SNAKE_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def _words(text: str) -> frozenset[str]:
    return frozenset(text.split())


_JAVA_RESERVED = _words(
    """
    abstract assert boolean break byte case catch char class const continue default do double
    else enum extends final finally float for goto if implements import instanceof int interface
    long native new package private protected public return short static strictfp super switch
    synchronized this throw throws transient try void volatile while _ true false null
    """
)
_KOTLIN_HARD_KEYWORDS = _words(
    """
    as break class continue do else false for fun if in interface is null object package return
    super this throw true try typealias typeof val var when while
    """
)
_TYPESCRIPT_RESERVED = _words(
    """
    break case catch class const continue debugger default delete do else enum export extends
    false finally for function if import in instanceof new null return super switch this throw
    true try typeof var void while with implements interface let package private protected
    public static yield await
    """
)
_GO_KEYWORDS = _words(
    """
    break case chan const continue default defer else fallthrough for func go goto if import
    interface map package range return select struct switch type var
    """
)
_RUST_KEYWORDS = _words(
    """
    as async await break const continue crate dyn else enum extern false fn for if impl in let
    loop match mod move mut pub ref return self Self static struct super trait true type unsafe use
    where while abstract become box do final macro override priv try typeof unsized virtual yield
    """
)
RESERVED_WORDS: Mapping[Language, frozenset[str]] = {
    Language.PYTHON: frozenset(keyword.kwlist),
    Language.TYPESCRIPT: _TYPESCRIPT_RESERVED,
    Language.JAVA: _JAVA_RESERVED,
    Language.KOTLIN: _KOTLIN_HARD_KEYWORDS,
    Language.GO: _GO_KEYWORDS,
    Language.RUST: _RUST_KEYWORDS,
}
PYTHON_BUILTINS = frozenset(name for name in dir(builtins) if not name.startswith("_"))
PYTHON_TYPE_IMPORTS: Mapping[Scalar, str] = {Scalar.DATE: "date", Scalar.DECIMAL: "Decimal"}
"""The name a Python stub imports for each scalar that is not a builtin."""


@dataclass(frozen=True, slots=True)
class FunctionNames:
    """`names` of a function-kind request job: the function and each canonical parameter."""

    function: str
    params: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class ClassNames:
    """`names` of a class-kind request job: the class and each canonical method."""

    class_name: str
    methods: Mapping[str, str]


type SymbolNames = FunctionNames | ClassNames


@dataclass(frozen=True, slots=True)
class ReservedNameConflict:
    name: str
    """The canonical name from meta.yaml."""
    language: Language
    symbol: str
    """The name after conversion for `language`, which is a reserved word there."""


def snake_case(name: str) -> str:
    """`getHTTPCode` becomes `get_http_code`."""
    return _SNAKE_CASE_BOUNDARY.sub("_", name).lower()


def member_name(canonical: str, language: Language) -> str:
    """The name of a function, method or parameter in `language`."""
    match language:
        case Language.PYTHON | Language.RUST:
            return snake_case(canonical)
        case Language.TYPESCRIPT | Language.JAVA | Language.KOTLIN | Language.GO:
            return canonical
        case _:
            assert_never(language)


def symbol_names(signature: Signature, language: Language) -> SymbolNames:
    if isinstance(signature, FunctionSignature):
        return FunctionNames(
            member_name(signature.name, language), _param_names(signature.params, language)
        )
    methods = {method.name: member_name(method.name, language) for method in signature.methods}
    return ClassNames(signature.name, methods)


def is_reserved(symbol: str, language: Language) -> bool:
    return symbol in RESERVED_WORDS[language]


def reserved_name_conflicts(
    signature: Signature, languages: Iterable[Language]
) -> tuple[ReservedNameConflict, ...]:
    """Every name that is a reserved word in one of `languages` after conversion (`cstudy verify`
    S3). A language the problem does not list never gets a stub, so it cannot conflict."""
    listed = tuple(languages)
    return tuple(
        ReservedNameConflict(declared.name, language, symbol)
        for declared in _declared_names(signature)
        for language in listed
        if is_reserved(symbol := declared.symbol(language), language)
    )


def shadowed_python_builtins(signature: Signature) -> tuple[str, ...]:
    """Python names that shadow a builtin such as `list` or `sum` (`cstudy verify` warns)."""
    return _python_names_in(signature, PYTHON_BUILTINS)


def shadowed_python_imports(signature: Signature) -> tuple[str, ...]:
    """Python names equal to a type the stub imports for this signature: `date` where it uses
    `date`, `Decimal` where it uses `decimal` (`cstudy verify` warns).
    """
    used = {scalar for declared in declared_types(signature) for scalar in scalars_of(declared)}
    imported = {name for scalar, name in PYTHON_TYPE_IMPORTS.items() if scalar in used}
    return _python_names_in(signature, imported)


def _python_names_in(signature: Signature, names: Set[str]) -> tuple[str, ...]:
    """The signature's Python names that are in `names`, each once, in declaration order."""
    python_names = (declared.symbol(Language.PYTHON) for declared in _declared_names(signature))
    return tuple(dict.fromkeys(name for name in python_names if name in names))


def _param_names(params: tuple[Param, ...], language: Language) -> dict[str, str]:
    return {param.name: member_name(param.name, language) for param in params}


@dataclass(frozen=True, slots=True)
class _DeclaredName:
    name: str
    is_class: bool

    def symbol(self, language: Language) -> str:
        return self.name if self.is_class else member_name(self.name, language)


def _declared_names(signature: Signature) -> Iterator[_DeclaredName]:
    if isinstance(signature, ClassSignature):
        yield _DeclaredName(signature.name, is_class=True)
        yield from _param_declarations(signature.constructor_params)
        for method in signature.methods:
            yield _DeclaredName(method.name, is_class=False)
            yield from _param_declarations(method.params)
        return
    yield _DeclaredName(signature.name, is_class=False)
    yield from _param_declarations(signature.params)


def _param_declarations(params: tuple[Param, ...]) -> Iterator[_DeclaredName]:
    return (_DeclaredName(param.name, is_class=False) for param in params)
