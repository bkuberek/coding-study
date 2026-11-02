"""tokio, vendored for Rust projects on the virtual clock
(docs/specs/runners.md#rust-build-details): a crate that declares it as a project may builds and
runs a paused-clock test offline, from the runtime copy a workspace refresh makes, with an empty
`CARGO_HOME`."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from coding_study.adapters.languages.rust.build_files import vendored_source_arguments
from coding_study.adapters.runner_runtime import RunnerRuntime
from coding_study.domain.project import RUST_CLOCK_CRATES
from tests.helpers import REPOSITORY_ROOT

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(shutil.which("cargo") is None, reason="needs Rust"),
]

PAUSED_CLOCK_TEST = """\
use std::time::Duration;

use tokio::time::Instant;

#[tokio::test(start_paused = true)]
async fn a_timeout_of_thirty_seconds_takes_no_time() {
    let start = Instant::now();
    let waited = tokio::time::timeout(Duration::from_secs(30), std::future::pending::<()>()).await;
    assert!(waited.is_err());
    assert_eq!(start.elapsed().as_millis(), 30_000);
}
"""


def test_a_crate_on_tokio_tests_on_the_paused_clock_offline(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    runtime = RunnerRuntime(REPOSITORY_ROOT / "runners", workspace).ensure()
    crate = tmp_path / "waits"
    (crate / "src").mkdir(parents=True)
    (crate / "tests").mkdir()
    dependencies = "".join(f"{name} = {spec}\n" for name, spec in RUST_CLOCK_CRATES.items())
    (crate / "Cargo.toml").write_text(
        '[package]\nname = "waits"\nedition = "2021"\nrust-version = "1.80"\n\n'
        f"[dependencies]\n{dependencies}"
    )
    (crate / "src" / "lib.rs").write_text("")
    (crate / "tests" / "level_1.rs").write_text(PAUSED_CLOCK_TEST)
    command = [
        *("cargo", "test", "--offline", "--quiet"),
        *vendored_source_arguments(runtime / "rust" / "vendor"),
    ]
    environment = {
        **{key: value for key, value in os.environ.items() if not key.startswith("CARGO")},
        "CARGO_HOME": str(tmp_path / "cargo-home"),
        "CARGO_TARGET_DIR": str(tmp_path / "target"),
    }
    done = subprocess.run(
        command, cwd=crate, env=environment, capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stderr[-2000:]
    assert "1 passed" in done.stdout
