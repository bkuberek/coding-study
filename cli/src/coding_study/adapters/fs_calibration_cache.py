"""Reference timings for time limits, in `.cs/calibration/<lang>/<slug>.json`.

Spec: docs/specs/performance-analysis.md#calibration. One file per language and problem holds
the latest calibration; its key also hashes the machine id, so a copied `.cs/` directory never
supplies another machine's timings. An unreadable entry counts as a miss.
"""

import hashlib
import json
import os
import platform
from pathlib import Path

from coding_study.domain.problem import Language
from coding_study.domain.time_limits import Calibration

CALIBRATION_DIRECTORY = ".cs/calibration"
FORMAT_VERSION = 1


def local_machine_id() -> str:
    """Host name, architecture, processor and core count: what decides reference timings."""
    parts = (platform.node(), platform.machine(), platform.processor(), str(os.cpu_count()))
    return hashlib.sha256("\0".join(parts).encode()).hexdigest()


class FsCalibrationCache:
    def __init__(self, root: Path, machine_id: str) -> None:
        self._directory = root / CALIBRATION_DIRECTORY
        self._machine_id = machine_id

    def load(self, language: Language, slug: str, key: str) -> Calibration | None:
        try:
            document = json.loads(self._entry(language, slug).read_text(encoding="utf-8"))
            if document["version"] != FORMAT_VERSION or document["key"] != self._stored(key):
                return None
            cases = {str(case_id): int(ns) for case_id, ns in document["cases"].items()}
            return Calibration(str(document["approach"]), cases)
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return None

    def save(self, language: Language, slug: str, key: str, calibration: Calibration) -> None:
        entry = self._entry(language, slug)
        entry.parent.mkdir(parents=True, exist_ok=True)
        document = {
            "version": FORMAT_VERSION,
            "key": self._stored(key),
            "approach": calibration.approach_id,
            "cases": dict(calibration.case_ns),
        }
        entry.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    def _entry(self, language: Language, slug: str) -> Path:
        return self._directory / language / f"{slug}.json"

    def _stored(self, key: str) -> str:
        return hashlib.sha256(f"{key}\0{self._machine_id}".encode()).hexdigest()
