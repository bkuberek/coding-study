# Vendored crates

Rust builds run with `cargo build --offline` and resolve crates.io from this directory: `cstudy` passes `--config source.crates-io.replace-with=...` and `--config source.<name>.directory=<this directory>`, the workspace's `rust/.cargo/config.toml` points the editor here, and `runners/rust/.cargo/config.toml` does the same for `cargo test` (docs/specs/runners.md#rust-build-details). Nothing is downloaded.

| Crate | Version | Why | Features |
|---|---|---|---|
| `rust_decimal` | 1.43.0 | `decimal` | `maths` only; its `std` feature adds no code we use but locks (and would vendor) 48 optional crates through weak `dep?/std` features |
| `chrono` | 0.4.45 | `date` (`NaiveDate`) | `std` only; the default `clock` feature pulls the time zone crates |
| `arrayvec` | 0.7.8 | dependency of `rust_decimal` | |
| `num-traits` | 0.2.19 | dependency of `rust_decimal` and `chrono` | |
| `autocfg` | 1.5.1 | build dependency of `num-traits` | |
| `tokio` | 1.53.3 | the runtime and paused clock of projects on the virtual clock | `macros`, `rt`, `sync`, `test-util`, `time`; declared by `cs_runner`'s `clock` feature, which only a clock project's harness turns on. 1.53 is the newest release whose MSRV (1.71) is within cstudy's Rust 1.80: 1.54 needs 1.85 |
| `tokio-macros` | 2.7.2 | `#[tokio::test]` and `select!`, through tokio's `macros` | |
| `pin-project-lite` | 0.2.17 | dependency of `tokio` | |
| `proc-macro2` | 1.0.107 | dependency of `tokio-macros` | |
| `quote` | 1.0.47 | dependency of `tokio-macros` | |
| `syn` | 3.0.9 | dependency of `tokio-macros` | |
| `unicode-ident` | 1.0.27 | dependency of `proc-macro2` and `syn` | |

Each crate keeps its `Cargo.toml`, `src/`, `build.rs`, `README.md` (the `rust_decimal` build script reads it) and license files. Tests, benchmarks, examples and CI files are removed, together with the `[[test]]`, `[[bench]]` and `[[example]]` tables that name them, and so are the `tests` directories under `src/` (tokio's unit tests, `#[cfg(test)]` modules that a dependency never compiles); `.cargo-checksum.json` lists the checksums of the remaining files; its `package` checksum, which `Cargo.lock` repeats, is the crates.io one. (The workspace's runner runtime never copies a directory named `tests`, at any depth, and Cargo checks every file a checksum lists, so the crates could not keep them.)

To update, change the versions in `cs_runner/Cargo.toml`, then, with an empty `CARGO_HOME` so no configuration of yours applies:

```sh
rm -rf vendor && CARGO_HOME=$(mktemp -d) cargo vendor vendor
python3 trim_vendor.py vendor   # the script below
```

and restore this README. Check the new `Cargo.lock` for crates you did not expect: a weak dependency feature locks optional crates that are never built.

```python
"""Trim `cargo vendor` output to what a build reads: usage `python trim_vendor.py <vendor dir>`."""

import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

KEPT_FILES = {"Cargo.toml", "build.rs", "README.md", ".cargo-checksum.json"}
KEPT_DIRECTORIES = {"src"}
NESTED_TESTS = "tests"
LICENSE = re.compile(r"^(LICEN[CS]E|COPYING|NOTICE)", re.IGNORECASE)
TARGET_TABLE = re.compile(r"^\[\[(?:test|bench|example)\]\]\n(?:(?!\[).*\n)*", re.MULTILINE)
CHECKSUM = ".cargo-checksum.json"


def trim(crate: Path) -> None:
    for path in crate.iterdir():
        if path.is_dir() and path.name not in KEPT_DIRECTORIES:
            shutil.rmtree(path)
        elif path.is_file() and path.name not in KEPT_FILES and not LICENSE.match(path.name):
            path.unlink()
    for nested in sorted(crate.rglob(NESTED_TESTS), reverse=True):
        if nested.is_dir():
            shutil.rmtree(nested)
    manifest = crate / "Cargo.toml"
    manifest.write_text(TARGET_TABLE.sub("", manifest.read_text()))
    checksum = crate / CHECKSUM
    package = json.loads(checksum.read_text())["package"]
    files = {
        path.relative_to(crate).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(crate.rglob("*"))
        if path.is_file() and path.name != CHECKSUM
    }
    checksum.write_text(json.dumps({"files": files, "package": package}, sort_keys=True))


for crate in sorted(Path(sys.argv[1]).iterdir()):
    if (crate / "Cargo.toml").is_file():
        trim(crate)
```
