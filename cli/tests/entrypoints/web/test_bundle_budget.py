"""The committed front end stays within the page-weight budget of NFR-12
(docs/specs/web-ui.md#front-end-assets): the whole bundle without the Vim chunk is at most 1 MB raw
and 350 KB gzip, and what the page loads before a file of one language is editable is at most
600 KB raw. A KB is 1024 bytes, as `tools/web-ui/build.sh` prints sizes.

What the page loads is the static-import closure of `app.js`, plus `app.css`; opening a file adds
the closure of the editor chunk and of the file's language chunk. A chunk another one reaches only
through `import()` is fetched when it is first used, so it does not count until then.
"""

import gzip
import re
from pathlib import Path

import pytest

from tests.helpers import REPOSITORY_ROOT

STATIC = REPOSITORY_ROOT / "cli" / "src" / "coding_study" / "entrypoints" / "web" / "static"
KB = 1024
WHOLE_RAW_KB = 1024
WHOLE_GZIP_KB = 350
EDITABLE_RAW_KB = 600
STATIC_IMPORT = re.compile(r'(?:from|import)\s*"(\.{1,2}/[^"]+\.js)"')
DYNAMIC_IMPORT = re.compile(r'import\("(\.{1,2}/[^"]+\.js)"\)')


def chunk(name: str) -> Path:
    (found,) = sorted((STATIC / "chunks").glob(f"{name}-*.js"))
    return found


def imports(path: Path) -> tuple[list[Path], list[Path]]:
    """The files a module imports statically and with `import()`."""
    text = path.read_text()
    dynamic = list(DYNAMIC_IMPORT.finditer(text))
    static = [
        match
        for match in STATIC_IMPORT.finditer(text)
        if not any(call.start() <= match.start() < call.end() for call in dynamic)
    ]
    return [(path.parent / m.group(1)).resolve() for m in static], [
        (path.parent / m.group(1)).resolve() for m in dynamic
    ]


def closure(entry: Path) -> set[Path]:
    """The module and everything it imports statically."""
    seen: set[Path] = set()
    pending = [entry.resolve()]
    while pending:
        current = pending.pop()
        if current not in seen:
            seen.add(current)
            pending.extend(imports(current)[0])
    return seen


def raw_kb(files: set[Path]) -> float:
    return sum(path.stat().st_size for path in files) / KB


def gzip_kb(files: set[Path]) -> float:
    return sum(len(gzip.compress(path.read_bytes(), 9)) for path in files) / KB


def page() -> set[Path]:
    return closure(STATIC / "app.js") | {(STATIC / "app.css").resolve()}


def languages() -> list[Path]:
    """The language chunks the editor fetches on demand; Vim is not one of them."""
    fetched = set(imports(chunk("editor"))[1])
    return sorted(path for path in fetched if not path.name.startswith("vim-"))


@pytest.mark.parametrize("language", languages(), ids=lambda path: path.name.split("-")[0])
def test_a_file_of_any_language_is_editable_within_the_raw_budget(language: Path):
    loaded = page() | closure(chunk("editor")) | closure(language)
    assert raw_kb(loaded) <= EDITABLE_RAW_KB


def test_the_bundle_without_vim_is_within_the_raw_budget():
    files = {
        path.resolve()
        for path in STATIC.rglob("*")
        if path.suffix in {".js", ".css"} and not path.name.startswith("vim-")
    }
    assert raw_kb(files) <= WHOLE_RAW_KB


def test_the_bundle_without_vim_is_within_the_gzip_budget():
    files = {
        path.resolve()
        for path in STATIC.rglob("*")
        if path.suffix in {".js", ".css"} and not path.name.startswith("vim-")
    }
    assert gzip_kb(files) <= WHOLE_GZIP_KB
