"""The committed front end stays within the page-weight budget of NFR-12
(docs/specs/web-ui.md#front-end-assets): the whole bundle without the Vim, code-intelligence and
Mermaid chunks is at most 1,200 KB raw and 400 KB gzip, and what the page loads before a file of
one language is editable is at most 600 KB raw. The code-intelligence chunk has a budget of its
own, at most 64 KB raw and 24 KB gzip, and holds no `marked`. Mermaid, which draws a guide's
diagrams, has its own too, at most 3,584 KB raw and 1,024 KB gzip with every diagram type it can
draw, and loads only when a guide with a diagram opens. A KB is 1024 bytes, as
`tools/web-ui/build.sh` prints sizes.

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
WHOLE_RAW_KB = 1200
WHOLE_GZIP_KB = 400
EDITABLE_RAW_KB = 600
INTELLIGENCE_RAW_KB = 64
INTELLIGENCE_GZIP_KB = 24
DIAGRAMS_RAW_KB = 3584
DIAGRAMS_GZIP_KB = 1024
STATIC_IMPORT = re.compile(r'(?:from|import)\s*"(\.{1,2}/[^"]+\.js)"')
DYNAMIC_IMPORT = re.compile(r'import\("(\.{1,2}/[^"]+\.js)"\)')
STYLESHEET = re.compile(r'"(chunks/[^"]+\.css)"')


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


def intelligence() -> set[Path]:
    """The code-intelligence chunk, the chunks only it imports and the stylesheets it links: what
    loads when the first file with a language server opens, and nothing the page or the editor
    already holds."""
    entry = chunk("code-intelligence")
    held = page() | closure(chunk("editor"))
    linked = {
        (STATIC / name).resolve()
        for module in closure(entry) - held
        for name in STYLESHEET.findall(module.read_text())
    }
    return (closure(entry) - held) | linked


def reach(entry: Path, around: frozenset[Path] = frozenset()) -> set[Path]:
    """The module and every module it imports, statically or with `import()`, without going
    through a module of `around`."""
    seen: set[Path] = set()
    pending = [entry.resolve()]
    while pending:
        current = pending.pop()
        if current not in seen and current not in around:
            seen.add(current)
            static, dynamic = imports(current)
            pending.extend([*static, *dynamic])
    return seen


def diagrams() -> set[Path]:
    """The diagrams chunk, which the Guides view fetches with `import()` when a guide with a
    diagram opens, and Mermaid with every diagram type it draws: all it reaches that the rest of
    the page does not."""
    entry = chunk("diagrams").resolve()
    return reach(entry) - reach(STATIC / "app.js", frozenset({entry}))


def without_optional_chunks() -> set[Path]:
    """Every script and stylesheet but the Vim chunk, the code-intelligence files and Mermaid's."""
    optional = intelligence() | diagrams()
    return {
        path.resolve()
        for path in STATIC.rglob("*")
        if path.suffix in {".js", ".css"}
        and not path.name.startswith("vim-")
        and path.resolve() not in optional
    }


def languages() -> list[Path]:
    """The language chunks the editor fetches on demand; Vim is not one of them."""
    fetched = set(imports(chunk("editor"))[1])
    return sorted(path for path in fetched if not path.name.startswith("vim-"))


@pytest.mark.parametrize("language", languages(), ids=lambda path: path.name.split("-")[0])
def test_a_file_of_any_language_is_editable_within_the_raw_budget(language: Path):
    loaded = page() | closure(chunk("editor")) | closure(language)
    assert raw_kb(loaded) <= EDITABLE_RAW_KB


def test_the_bundle_without_vim_and_code_intelligence_is_within_the_raw_budget():
    assert raw_kb(without_optional_chunks()) <= WHOLE_RAW_KB


def test_the_bundle_without_vim_and_code_intelligence_is_within_the_gzip_budget():
    assert gzip_kb(without_optional_chunks()) <= WHOLE_GZIP_KB


def test_the_code_intelligence_chunk_is_within_its_raw_budget():
    assert raw_kb(intelligence()) <= INTELLIGENCE_RAW_KB


def test_the_code_intelligence_chunk_is_within_its_gzip_budget():
    assert gzip_kb(intelligence()) <= INTELLIGENCE_GZIP_KB


def test_the_page_loads_neither_code_intelligence_module_until_the_preference_is_on():
    """The link between the editors and the sessions is a chunk of its own, fetched with
    `import()` once `code_intelligence` is on, and it fetches the code-intelligence chunk."""
    loaded = page() | closure(chunk("editor"))
    link = chunk("intelligence").resolve()
    fetched_by_page = {
        found for module in page() if module.suffix == ".js" for found in imports(module)[1]
    }
    assert (
        chunk("code-intelligence").resolve() in loaded,
        link in loaded,
        link in fetched_by_page,
        chunk("code-intelligence").resolve() in imports(link)[1],
    ) == (False, False, True, True)


def test_mermaid_is_within_its_raw_budget():
    assert raw_kb(diagrams()) <= DIAGRAMS_RAW_KB


def test_mermaid_is_within_its_gzip_budget():
    assert gzip_kb(diagrams()) <= DIAGRAMS_GZIP_KB


def test_only_a_guide_with_a_diagram_fetches_mermaid():
    """The Guides view is a chunk the page fetches when it first opens, and it fetches the
    diagrams chunk with `import()` only once a guide has a diagram: neither the page, nor a file
    being edited, nor the Guides view itself loads any of Mermaid."""
    view = chunk("guides").resolve()
    fetched_by_page = {
        found for module in page() if module.suffix == ".js" for found in imports(module)[1]
    }
    loaded = page() | closure(chunk("editor")) | closure(view)
    assert (
        view in fetched_by_page,
        chunk("diagrams").resolve() in imports(view)[1],
        sorted(path.name for path in loaded & diagrams()),
    ) == (True, True, [])


def test_mermaid_holds_every_diagram_type_a_guide_may_draw():
    """The types `cstudy verify` allows in a guide (docs/specs/guides.md#diagrams)."""
    names = {path.name.split("-")[0] for path in diagrams()}
    assert {"flowDiagram", "sequenceDiagram", "stateDiagram", "classDiagram", "erDiagram"} <= names


def test_no_script_but_mermaids_holds_marked():
    """`@codemirror/lsp-client` imports `marked`; the build gives it an escaping stand-in, so its
    source, which names its repository in an error message, is in no script the page or the
    editor loads. Mermaid's chunks hold it, to read the Markdown a diagram's label may hold."""
    mermaid = diagrams()
    holding = [
        path.name
        for path in STATIC.rglob("*.js")
        if path.resolve() not in mermaid and "github.com/markedjs/marked" in path.read_text()
    ]
    assert holding == []


def test_the_stand_in_for_marked_is_in_the_code_intelligence_chunk():
    assert "&#39;" in chunk("code-intelligence").read_text()
