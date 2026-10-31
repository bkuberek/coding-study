import hashlib
import json
import sys
from importlib.metadata import version
from pathlib import Path

from coding_study.adapters.serve_install import InstalledWebUi

EDITOR = b"export const editor = 1;\n"
CHUNK = b"export const go = 2;\n"


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def static_directory(root: Path, files: dict[str, bytes], digests: dict[str, str]) -> Path:
    """`files` written under `root`, with a manifest.json naming `digests`."""
    for path, content in files.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_bytes(content)
    (root / "manifest.json").write_text(json.dumps({"entry": "editor.js", "files": digests}))
    return root


def built(root: Path) -> Path:
    files = {"editor.js": EDITOR, "chunks/go-6P5FBZMG.js": CHUNK}
    return static_directory(root, files, {path: digest(data) for path, data in files.items()})


def test_matching_assets_report_their_total_size(tmp_path):
    assets = InstalledWebUi(built(tmp_path)).assets()
    assert (assets.size_bytes, assets.problem) == (len(EDITOR) + len(CHUNK), None)


def test_a_missing_asset_is_named(tmp_path):
    (built(tmp_path) / "chunks" / "go-6P5FBZMG.js").unlink()
    assert InstalledWebUi(tmp_path).assets().problem == "missing chunks/go-6P5FBZMG.js"


def test_a_changed_asset_is_named(tmp_path):
    (built(tmp_path) / "editor.js").write_bytes(b"changed")
    assert InstalledWebUi(tmp_path).assets().problem == "editor.js does not match manifest.json"


def test_the_first_failing_asset_in_path_order_is_named(tmp_path):
    files = {"b.js": EDITOR, "a.js": CHUNK}
    static_directory(tmp_path, files, {"b.js": "0" * 64, "a.js": "0" * 64})
    assert InstalledWebUi(tmp_path).assets().problem == "a.js does not match manifest.json"


def test_a_missing_manifest_is_named(tmp_path):
    assert InstalledWebUi(tmp_path).assets().problem == "missing manifest.json"


def test_a_manifest_without_files_is_unreadable(tmp_path):
    (tmp_path / "manifest.json").write_text('{"entry": "editor.js"}')
    assert InstalledWebUi(tmp_path).assets().problem == "unreadable manifest.json"


def test_a_manifest_that_is_not_json_is_unreadable(tmp_path):
    (tmp_path / "manifest.json").write_text("{files")
    assert InstalledWebUi(tmp_path).assets().problem == "unreadable manifest.json"


def test_the_server_libraries_report_their_versions(tmp_path):
    assert InstalledWebUi(tmp_path).server_libraries().versions == (
        f"starlette {version('starlette')}",
        f"uvicorn {version('uvicorn')}",
    )


def test_a_library_that_does_not_import_is_named(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "uvicorn", None)
    problem = InstalledWebUi(tmp_path).server_libraries().problem or ""
    assert problem.startswith("uvicorn does not import: ")
