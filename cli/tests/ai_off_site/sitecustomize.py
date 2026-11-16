"""The probe of a child `cstudy` in `tests/test_ai_off.py`, loaded by Python at start-up when this
directory leads `PYTHONPATH`.

It arms the rules of `tests/network_guard.py`, so the child refuses any connection or name lookup
off the loopback, and writes one JSON line to the file `AI_OFF_PROBE_LOG` names, when the process
exits: the refusals, the reads of `credentials.toml`, and the `coding_study.adapters.ai` modules
that were imported. A process that leaves no line was not probed.
"""

import atexit
import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType

LOG_VARIABLE = "AI_OFF_PROBE_LOG"
CREDENTIALS_FILE = "credentials.toml"
PROVIDER_PACKAGE = "coding_study.adapters.ai"


def _load_guard() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "network_guard.py"
    spec = importlib.util.spec_from_file_location("ai_off_network_guard", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_credential_reads: list[str] = []


def _audit(event: str, args: tuple[object, ...]) -> None:
    if event == "open" and isinstance(args[0], str | bytes | os.PathLike):
        path = os.fsdecode(args[0])
        if Path(path).name == CREDENTIALS_FILE:
            _credential_reads.append(path)


def _record(guard: ModuleType, log: str) -> None:
    imported = sorted(
        name
        for name in sys.modules
        if name == PROVIDER_PACKAGE or name.startswith(f"{PROVIDER_PACKAGE}.")
    )
    line = {
        "pid": os.getpid(),
        "argv": sys.argv,
        "refused": guard.disarm(),
        "credential_reads": _credential_reads,
        "provider_modules": imported,
    }
    with Path(log).open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(line) + "\n")


def _install() -> None:
    log = os.environ.get(LOG_VARIABLE)
    if not log:
        return
    guard = _load_guard()
    guard.install()
    guard.arm()
    sys.addaudithook(_audit)
    atexit.register(_record, guard, log)


_install()
