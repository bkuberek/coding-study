"""Per-language symbol names (docs/specs/problem-format.md#naming-rules).

Canonical names are lowerCamelCase (classes PascalCase). Python and Rust convert functions,
methods and parameters to snake_case; TypeScript, Java and Kotlin keep the canonical names. Go
keeps them too, except that methods are exported (PascalCase) because reflection only finds
exported ones. Runners never convert names: the CLI sends them in the request
(docs/specs/runners.md#request-file).
"""

import builtins
import keyword
import re
from collections.abc import Iterable, Iterator, Mapping, Set
from dataclasses import dataclass
from enum import StrEnum
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


@dataclass(frozen=True, slots=True)
class StubImport:
    """A name a stub imports for a scalar that is not built into the language."""

    name: str
    kind: str
    """`type` or `package`, for messages."""


STUB_IMPORTS: Mapping[Language, Mapping[Scalar, StubImport]] = {
    Language.PYTHON: {
        Scalar.DATE: StubImport("date", "type"),
        Scalar.DECIMAL: StubImport("Decimal", "type"),
    },
    Language.TYPESCRIPT: {},
    Language.JAVA: {},
    Language.KOTLIN: {},
    Language.GO: {
        Scalar.DATE: StubImport("time", "package"),
        Scalar.DECIMAL: StubImport("decimal", "package"),
    },
    Language.RUST: {
        Scalar.DATE: StubImport("NaiveDate", "type"),
        Scalar.DECIMAL: StubImport("Decimal", "type"),
    },
}
"""The names a stub imports for `date` and `decimal` that a signature's names can collide with.
TypeScript, Java and Kotlin are not checked."""
DECLARED_BESIDE_IMPORTS = frozenset({Language.GO, Language.RUST})
"""Languages where the stub's function or class is declared in the scope of its imports, so one
with an imported name does not compile (Go: `time already declared through import`, Rust:
E0255). A Python definition only rebinds the name."""


class NameRole(StrEnum):
    """What a name is for, where a language's naming rule depends on it."""

    FUNCTION = "function"
    METHOD = "method"
    PARAMETER = "parameter"


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
    constructor: str | None = None
    """Go and Rust build an instance by calling a function, not by naming the class."""


type SymbolNames = FunctionNames | ClassNames


@dataclass(frozen=True, slots=True)
class ShadowedImport:
    language: Language
    symbol: str
    """The name in `language`, equal to the import's."""
    imported: StubImport
    breaks_stub: bool
    """The function or the class has the name, in a language that declares it beside the
    import; otherwise a parameter or method only hides the import from the code after it."""


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


def member_name(canonical: str, language: Language, role: NameRole) -> str:
    """The name of a function, method or parameter in `language`."""
    match language:
        case Language.PYTHON | Language.RUST:
            return snake_case(canonical)
        case Language.TYPESCRIPT | Language.JAVA | Language.KOTLIN:
            return canonical
        case Language.GO:
            return canonical[:1].upper() + canonical[1:] if role is NameRole.METHOD else canonical
        case _:
            assert_never(language)


def constructor_name(class_name: str, language: Language) -> str | None:
    """The function that creates an instance in languages without constructors: Go's
    `NewLRUCache` and Rust's `new`. None where the class itself is called."""
    match language:
        case Language.GO:
            return f"New{class_name}"
        case Language.RUST:
            return "new"
        case Language.PYTHON | Language.TYPESCRIPT | Language.JAVA | Language.KOTLIN:
            return None
        case _:
            assert_never(language)


def symbol_names(signature: Signature, language: Language) -> SymbolNames:
    if isinstance(signature, FunctionSignature):
        return FunctionNames(
            member_name(signature.name, language, NameRole.FUNCTION),
            _param_names(signature.params, language),
        )
    methods = {
        method.name: member_name(method.name, language, NameRole.METHOD)
        for method in signature.methods
    }
    return ClassNames(signature.name, methods, constructor_name(signature.name, language))


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


def shadowed_imports(
    signature: Signature, languages: Iterable[Language]
) -> tuple[ShadowedImport, ...]:
    """Names equal to a name the stub of one of `languages` imports for this signature: Python
    `date` where it uses `date`, Go `time`, Rust `Decimal` where it uses `decimal` (`cstudy
    verify` S3). Each name once per language, in declaration order."""
    used = {scalar for declared in declared_types(signature) for scalar in scalars_of(declared)}
    shadows: list[ShadowedImport] = []
    for language in languages:
        imports = {
            stub_import.name: stub_import
            for scalar, stub_import in STUB_IMPORTS[language].items()
            if scalar in used
        }
        breaks: dict[str, bool] = {}
        for declared in _declared_names(signature):
            symbol = declared.symbol(language)
            if symbol in imports:
                top_level = declared.role in (None, NameRole.FUNCTION)
                breaks[symbol] = breaks.get(symbol, False) or top_level
        beside = language in DECLARED_BESIDE_IMPORTS
        shadows += [
            ShadowedImport(language, symbol, imports[symbol], beside and top_level)
            for symbol, top_level in breaks.items()
        ]
    return tuple(shadows)


def _python_names_in(signature: Signature, names: Set[str]) -> tuple[str, ...]:
    """The signature's Python names that are in `names`, each once, in declaration order."""
    python_names = (declared.symbol(Language.PYTHON) for declared in _declared_names(signature))
    return tuple(dict.fromkeys(name for name in python_names if name in names))


def _param_names(params: tuple[Param, ...], language: Language) -> dict[str, str]:
    return {param.name: member_name(param.name, language, NameRole.PARAMETER) for param in params}


@dataclass(frozen=True, slots=True)
class _DeclaredName:
    name: str
    role: NameRole | None
    """None for the class, which every language spells as declared."""

    def symbol(self, language: Language) -> str:
        return self.name if self.role is None else member_name(self.name, language, self.role)


def _declared_names(signature: Signature) -> Iterator[_DeclaredName]:
    if isinstance(signature, ClassSignature):
        yield _DeclaredName(signature.name, role=None)
        yield from _param_declarations(signature.constructor_params)
        for method in signature.methods:
            yield _DeclaredName(method.name, NameRole.METHOD)
            yield from _param_declarations(method.params)
        return
    yield _DeclaredName(signature.name, NameRole.FUNCTION)
    yield from _param_declarations(signature.params)


def _param_declarations(params: tuple[Param, ...]) -> Iterator[_DeclaredName]:
    return (_DeclaredName(param.name, NameRole.PARAMETER) for param in params)
