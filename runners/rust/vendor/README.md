# Vendored crates

Rust builds run with `cargo build --offline` and resolve crates.io from this directory: `cstudy` passes `--config source.crates-io.replace-with=...` and `--config source.<name>.directory=<this directory>`, the workspace's `rust/.cargo/config.toml` points the editor here, and `runners/rust/.cargo/config.toml` does the same for `cargo test` (docs/specs/runners.md#rust-build-details). Nothing is downloaded.

| Crate | Version | Why | Features |
|---|---|---|---|
| `rust_decimal` | 1.43.0 | `decimal` | `maths` only; its `std` feature adds no code we use but locks (and would vendor) 48 optional crates through weak `dep?/std` features |
| `chrono` | 0.4.45 | `date` (`NaiveDate`) | `std` only; the default `clock` feature pulls the time zone crates |
| `arrayvec` | 0.7.8 | dependency of `rust_decimal` | |
| `num-traits` | 0.2.19 | dependency of `rust_decimal` and `chrono` | |
| `autocfg` | 1.5.1 | build dependency of `num-traits` | |

Each crate keeps its `Cargo.toml`, `src/`, `build.rs`, `README.md` (the `rust_decimal` build script reads it) and license files. Tests, benchmarks, examples and CI files are removed, together with the `[[test]]`, `[[bench]]` and `[[example]]` tables that name them, and `.cargo-checksum.json` lists the checksums of the remaining files; its `package` checksum, which `Cargo.lock` repeats, is the crates.io one. (The workspace's runner runtime never copies a directory named `tests`, so the crates could not keep them.)

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
LICENSE = re.compile(r"^(LICEN[CS]E|COPYING|NOTICE)", re.IGNORECASE)
TARGET_TABLE = re.compile(r"^\[\[(?:test|bench|example)\]\]\n(?:(?!\[).*\n)*", re.MULTILINE)
CHECKSUM = ".cargo-checksum.json"


def trim(crate: Path) -> None:
    for path in crate.iterdir():
        if path.is_dir() and path.name not in KEPT_DIRECTORIES:
            shutil.rmtree(path)
        elif path.is_file() and path.name not in KEPT_FILES and not LICENSE.match(path.name):
            path.unlink()
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
