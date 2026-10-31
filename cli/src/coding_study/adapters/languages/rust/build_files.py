"""The Cargo side of the Rust build (docs/specs/runners.md#rust-build-details): the generated
manifests, the release profile, and what `cargo build --message-format=json` reports.

Diagnostics are classified by the primary span of each error-level message only. A call whose
signature does not match gets a child note "function defined here" in the user's file, but the
error itself is in the bridge, and only the bridge's errors become `load_error`s.
"""

import json
import re
import sys
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import cast

from coding_study.adapters.languages.rust.bridge import (
    ARGUMENT_PREFIX,
    GENERATED_HEADER,
    Bridge,
    BridgeTarget,
    Unavailable,
)
from coding_study.domain.errors import RunnerStartError
from coding_study.domain.naming import RAW_IDENTIFIER_PREFIX
from coding_study.domain.project import RUST_VENDORED_CRATES
from coding_study.domain.workspace_projects import RUST_VENDORED_SOURCE

EDITION = "2021"
RUST_VERSION = "1.80"
"""The oldest compiler cstudy supports (`cstudy doctor`); clippy suggests nothing newer."""
MANIFEST_FILE = "Cargo.toml"
WORKSPACE_SCOPES = ("test", "verify", "bench")
"""Each scope is a directory of harness packages, one per problem."""
SPLIT_DEBUGINFO = '"unpacked"' if sys.platform == "darwin" else '"off"'
"""Cargo's default for the platform: the debug info stays where the binary's symbolizer finds it,
also for the private copy each run launches."""
RELEASE_PROFILE: Mapping[str, str] = {
    "opt-level": "3",
    "overflow-checks": "true",
    "debug": '"line-tables-only"',
    "panic": '"unwind"',
    "strip": '"none"',
    "split-debuginfo": SPLIT_DEBUGINFO,
}
"""Optimized, so `--perf` numbers are real; an `i32` overflow panics instead of wrapping; line
tables give traces their lines, and the symbols and debug info stay in place so traces name
their functions; panics unwind, so one case's panic is caught. The build passes these as
`--config` too, which outranks a user's `config.toml`."""
DEV_PROFILE: Mapping[str, str] = {
    "opt-level": "0",
    "debug": "true",
    "overflow-checks": "true",
    "panic": '"unwind"',
    "strip": '"none"',
    "split-debuginfo": SPLIT_DEBUGINFO,
}
"""`cstudy test --debug`: no optimizations and full debug info, so a debugger sees every line and
variable; overflows and panics behave as in the release profile. Pinned the same way."""
RELEASE = "release"
DEV = "dev"
PROFILES: Mapping[str, Mapping[str, str]] = {RELEASE: RELEASE_PROFILE, DEV: DEV_PROFILE}
VENDOR_DIRECTORY = "vendor"
"""The vendored crates inside the runtime's `rust/` directory (runners/rust/vendor/README.md)."""
VENDORED_SOURCE = RUST_VENDORED_SOURCE
DECIMAL_DATE_CRATES: Mapping[str, str] = RUST_VENDORED_CRATES
"""The crates of `decimal` and `date`, declared as `cs_runner` declares them. A solution is a
module of the harness crate, so the harness depends on them directly for its `use` lines."""
USER_CRATE = "user"
"""The name a project harness gives the project's crate, as the bridge's module of a target."""
SYMBOL_CODES = frozenset({"E0412", "E0422", "E0425", "E0433", "E0583", "E0599", "E0603", "E0624"})
"""Errors that mean the target does not define a symbol the bridge calls (or keeps it private)."""
PRIVATE_CODES = frozenset({"E0603", "E0624"})
LABELLED_CODES = frozenset({"E0308"})
"""Errors whose primary span's label says what the message does not: `expected i32, found
i64`."""
SYMBOL_NOT_FOUND = "SymbolNotFound"
SIGNATURE_MISMATCH = "SignatureMismatch"
MAX_NOTES = 2
_ERROR = "error"
_NOTE_LEVELS = frozenset({"help", "note"})
_COMPILER_MESSAGE = "compiler-message"
_ARTIFACT = "compiler-artifact"
_EXTERNAL_FILE = re.compile(r"^(/rustc/|<)")
_EXPECTED_FOUND = re.compile(r"expected `(?P<expected>.+)`, found `(?P<found>.+)`")
_ARGUMENT = re.compile(rf"(?:&mut )?{ARGUMENT_PREFIX}(?P<name>\w+)")
_RAW_IDENTIFIER = re.compile(rf"\b{RAW_IDENTIFIER_PREFIX}(?=[A-Za-z_])")
"""rustc's spelling of a keyword name, `r#move`; not a raw string literal `r#"..."#`."""
_HELP = "help: "


@dataclass(frozen=True, slots=True)
class CompilerError:
    path: Path
    """The primary span's file, resolved against the directory `cargo build` ran in."""
    line: int
    column: int
    code: str
    message: str
    label: str
    notes: tuple[str, ...]
    """`help: ...` and `note: ...` lines from the error's children, those that suggest a
    replacement first, at most `MAX_NOTES`."""
    snippet: str = ""
    """The source text the primary span marks."""
    suggestions: tuple[str, ...] = ()
    """The children's lines that suggest a replacement, such as an item with a similar name."""

    def shown(self, path: str) -> tuple[str, ...]:
        """The error's lines with the file shown as `path`."""
        code = f"[{self.code}]" if self.code else ""
        repeated = self.label in self.message
        label = (f"    {self.label}",) if self.label and not repeated else ()
        notes = tuple(f"    {note}" for note in self.notes)
        return (f"{path}:{self.line}:{self.column}: error{code}: {self.message}", *label, *notes)


def workspace_members(build_directory: Path) -> list[str]:
    """Every harness package in the build directory, as `<scope>/<snake_slug>`. Cargo takes a
    glob that matches nothing as a path, so the members are listed one by one."""
    return sorted(
        manifest.parent.relative_to(build_directory).as_posix()
        for scope in WORKSPACE_SCOPES
        for manifest in (build_directory / scope).glob(f"*/{MANIFEST_FILE}")
    )


def workspace_manifest(members: list[str]) -> str:
    listed = "".join(f'    "{member}",\n' for member in members)
    profiles = "".join(
        f"\n[profile.{name}]\n" + "".join(f"{key} = {value}\n" for key, value in settings.items())
        for name, settings in PROFILES.items()
    )
    return (
        f'# {GENERATED_HEADER.removeprefix("// ")}\n[workspace]\nresolver = "2"\n'
        f"members = [\n{listed}]\n{profiles}"
    )


def package_manifest(name: str, runtime: str) -> str:
    """A harness package `name` whose `main.rs` is the bridge; `runtime` is the relative path to
    the runner runtime's `rust/` directory."""
    crates = "".join(f"{crate} = {spec}\n" for crate, spec in DECIMAL_DATE_CRATES.items())
    return (
        f'# {GENERATED_HEADER.removeprefix("// ")}\n[package]\nname = "{name}"\n'
        f'version = "0.0.0"\nedition = "{EDITION}"\nrust-version = "{RUST_VERSION}"\n'
        f"publish = false\n\n"
        f'[[bin]]\nname = "{name}"\npath = "main.rs"\n\n[dependencies]\n'
        f'cs_runner = {{ path = "{runtime}/cs_runner" }}\n'
        f'cs_support = {{ path = "{runtime}/cs_support" }}\n{crates}'
    )


def project_harness_manifest(name: str, crate: str, root: str, runtime: str) -> str:
    """A project's harness package `name`, depending on the crate `crate` at the relative path
    `root` under the name `user`, and on the runner crates at `runtime`, the relative path to the
    runtime's `rust/` directory (docs/specs/runners.md#rust-projects)."""
    user = f'{USER_CRATE} = {{ package = "{crate}", path = {json.dumps(root)} }}\n'
    return package_manifest(name, runtime).replace("[dependencies]\n", f"[dependencies]\n{user}")


def profile_arguments(profile: str = RELEASE) -> list[str]:
    return [
        argument
        for key, value in PROFILES[profile].items()
        for argument in ("--config", f"profile.{profile}.{key}={value}")
    ]


def vendored_source_arguments(vendor: Path) -> list[str]:
    """Resolve crates.io from the vendored copies in `vendor`, offline; like the profile, these
    outrank whatever source a user's `config.toml` sets."""
    return [
        "--config",
        f'source.crates-io.replace-with="{VENDORED_SOURCE}"',
        "--config",
        f"source.{VENDORED_SOURCE}.directory={json.dumps(str(vendor))}",
    ]


def compiler_errors(stdout: str, cwd: Path) -> tuple[CompilerError, ...]:
    """Every error-level compiler message with a primary span; summaries such as `aborting due
    to 2 previous errors` have none."""
    return tuple(error for _, error in target_errors(stdout, cwd))


def target_errors(stdout: str, cwd: Path) -> tuple[tuple[Path, CompilerError], ...]:
    """`compiler_errors` with the source root of the target that each was compiled for: a
    library and its unit tests both report an error of the library's files."""
    errors: list[tuple[Path, CompilerError]] = []
    for message in _messages(stdout, _COMPILER_MESSAGE):
        error = _compiler_error(_object(message.get("message")), cwd)
        if error is not None:
            target = Path(str(_object(message.get("target")).get("src_path", "")))
            errors.append(((cwd / target).resolve(), error))
    return tuple(errors)


def _compiler_error(diagnostic: dict[str, object], cwd: Path) -> CompilerError | None:
    if diagnostic.get("level") != _ERROR:
        return None
    span = _primary_span(diagnostic)
    if span is None:
        return None
    code = _object(diagnostic.get("code")).get("code")
    notes = _notes(diagnostic)
    return CompilerError(
        path=(cwd / str(span.get("file_name"))).resolve(),
        line=_integer(span.get("line_start")),
        column=_integer(span.get("column_start")),
        code=code if isinstance(code, str) else "",
        message=str(diagnostic.get("message", "")),
        label=str(span.get("label") or ""),
        notes=tuple(note.text for note in notes[:MAX_NOTES]),
        snippet=_snippet(span),
        suggestions=tuple(note.text for note in notes if note.suggests),
    )


def built_test_binaries(stdout: str) -> tuple[tuple[Path, Path], ...]:
    """Each test binary `cargo build --tests` built, with its target's source root."""
    built: list[tuple[Path, Path]] = []
    for artifact in _messages(stdout, _ARTIFACT):
        path = artifact.get("executable")
        if _object(artifact.get("profile")).get("test") is True and isinstance(path, str):
            source = _object(artifact.get("target")).get("src_path")
            built.append((Path(str(source)), Path(path)))
    return tuple(built)


def executable(stdout: str, name: str) -> Path | None:
    """The binary `cargo build` reported for the bin target `name`."""
    for artifact in _messages(stdout, _ARTIFACT):
        target = _object(artifact.get("target"))
        path = artifact.get("executable")
        if target.get("name") == name and isinstance(path, str):
            return Path(path)
    return None


def output_text(stdout: str, stderr: str) -> tuple[str, ...]:
    """What `cargo build` said, for a failure that is not a compiler error: the rendered
    messages and its own standard error."""
    rendered = [
        str(_object(message.get("message")).get("rendered") or "")
        for message in _messages(stdout, _COMPILER_MESSAGE)
    ]
    return (*(line for text in rendered for line in text.splitlines()), *stderr.splitlines())


def load_error(error: CompilerError, module: str, file_name: str) -> Unavailable:
    """The `load_error` of a target whose bridge code did not compile, in the user's terms: the
    bridge's module or crate `user` is the file `two_sum.rs` (a project's `src/lib.rs`), a type
    mismatch says which side is the user's, and a keyword name is the signature's `move`, not the
    bridge's `r#move`."""
    symbol = error.code in SYMBOL_CODES
    message = _mismatch(error) or error.message
    if symbol:
        notes = error.suggestions or error.notes
        helps = (note.removeprefix(_HELP) for note in notes if note.startswith(_HELP))
        message = "; ".join([message, *helps])
    if error.code in PRIVATE_CODES:
        message += "; declare it pub"
    message = (
        message.replace(f"module `{module}`", f"`{file_name}`")
        .replace(f"crate `{module}`", f"`{file_name}`")
        .replace(f"`{module}::", "`")
        .replace(f"{module}::", "")
    )
    message = _RAW_IDENTIFIER.sub("", message)
    return Unavailable(SYMBOL_NOT_FOUND if symbol else SIGNATURE_MISMATCH, message)


def marked_unavailable(
    targets: list[BridgeTarget],
    bridge: Bridge,
    errors: tuple[CompilerError, ...],
) -> list[BridgeTarget]:
    """`targets` with each one that owns a failing bridge line marked unavailable, with the
    first of its errors; a target whose module line failed (its file is missing) loses the
    module too. A failing line that no target owns means the generator is broken."""
    failures: dict[str, Unavailable] = {}
    missing_modules: set[str] = set()
    for error in errors:
        owner = bridge.owners.get(error.line)
        if owner is None:
            shown = error.shown(str(error.path))
            raise RunnerStartError("the generated Rust bridge does not compile", shown)
        if error.line in bridge.modules:
            missing_modules.add(owner)
        target = next(target for target in targets if target.target_id == owner)
        failures.setdefault(owner, load_error(error, target.module, target.shown_name))
    return [
        replace(
            target,
            unavailable=failures[target.target_id],
            with_module=target.target_id not in missing_modules,
        )
        if target.target_id in failures
        else target
        for target in targets
    ]


def _mismatch(error: CompilerError) -> str | None:
    """`E0308` as the bridge sees it: for an argument, rustc expects the user's parameter type and
    finds the declared one; for the result, the other way round."""
    found = _EXPECTED_FOUND.fullmatch(error.label) if error.code in LABELLED_CODES else None
    if found is None:
        return None
    expected, actual = found["expected"], found["found"]
    argument = _ARGUMENT.fullmatch(error.snippet)
    if argument:
        parameter = argument["name"]
        return (
            f"mismatched types: parameter `{parameter}` is `{expected}`, "
            f"the signature declares `{actual}`"
        )
    return f"mismatched types: the result is `{actual}`, the signature declares `{expected}`"


def _messages(stdout: str, reason: str) -> Iterator[dict[str, object]]:
    for line in stdout.splitlines():
        if not line.startswith("{"):
            continue
        try:
            message: object = json.loads(line)
        except ValueError:
            continue
        fields = _object(message)
        if fields.get("reason") == reason:
            yield fields


def _object(value: object) -> dict[str, object]:
    return cast("dict[str, object]", value) if isinstance(value, dict) else {}


def _list(value: object) -> list[object]:
    return cast("list[object]", value) if isinstance(value, list) else []


def _integer(value: object) -> int:
    return value if isinstance(value, int) else 0


def _primary_span(diagnostic: dict[str, object]) -> dict[str, object] | None:
    """The first primary span, followed out of a standard library macro to where it was
    called."""
    spans = [_object(span) for span in _list(diagnostic.get("spans"))]
    span = next((span for span in spans if span.get("is_primary") is True), None)
    while span is not None and _EXTERNAL_FILE.match(str(span.get("file_name", ""))):
        caller = _object(_object(span.get("expansion")).get("span"))
        span = caller or None
    return span


def _snippet(span: dict[str, object]) -> str:
    lines = [_object(line) for line in _list(span.get("text"))]
    if not lines:
        return ""
    first = lines[0]
    text = str(first.get("text", ""))
    start, end = _integer(first.get("highlight_start")), _integer(first.get("highlight_end"))
    return text[max(start - 1, 0) : max(end - 1, 0)]


@dataclass(frozen=True, slots=True)
class _Note:
    text: str
    suggests: bool


def _notes(diagnostic: dict[str, object]) -> list[_Note]:
    """The `help` and `note` children, those that suggest a replacement first: rustc may list a
    similarly named method after two notes about traits. A replacement the text already names is
    not repeated."""
    notes: list[_Note] = []
    for child in map(_object, _list(diagnostic.get("children"))):
        level, text = child.get("level"), child.get("message")
        if level not in _NOTE_LEVELS or not isinstance(text, str) or not text:
            continue
        spans = map(_object, _list(child.get("spans")))
        replacement = next((s.get("suggested_replacement") for s in spans), None)
        suggests = isinstance(replacement, str) and bool(replacement)
        named = suggests and f"`{replacement}`" in text
        suffix = f": `{replacement}`" if suggests and not named else ""
        notes.append(_Note(f"{level}: {text}{suffix}", suggests))
    return sorted(notes, key=lambda note: not note.suggests)
