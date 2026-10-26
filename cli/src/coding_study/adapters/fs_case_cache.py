"""Generated cases with expected values, cached in `.cs/cases/<slug>/<key>.json`.

The key hashes everything the cases depend on (docs/architecture.md#cache-directory-cstudy), so a
stale entry is never read; an unreadable entry counts as a miss.
"""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from coding_study.domain.cases import Expected, FunctionInput, JsonValue, OperationSequence
from coding_study.domain.generated_cases import GeneratedCase
from coding_study.domain.runs import RunInput

CASES_DIRECTORY = ".cs/cases"
FORMAT_VERSION = 1


class FsGeneratedCaseCache:
    def __init__(self, root: Path) -> None:
        self._directory = root / CASES_DIRECTORY

    def load(self, slug: str, key: str) -> Mapping[str, GeneratedCase] | None:
        try:
            document = json.loads(self._entry(slug, key).read_text(encoding="utf-8"))
            if document["version"] != FORMAT_VERSION:
                return None
            return {case_id: _case(case) for case_id, case in document["cases"].items()}
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def save(self, slug: str, key: str, cases: Mapping[str, GeneratedCase]) -> None:
        entry = self._entry(slug, key)
        entry.parent.mkdir(parents=True, exist_ok=True)
        document = {
            "version": FORMAT_VERSION,
            "cases": {case_id: _document(case) for case_id, case in cases.items()},
        }
        entry.write_text(json.dumps(document), encoding="utf-8")

    def _entry(self, slug: str, key: str) -> Path:
        return self._directory / slug / f"{key}.json"


def _document(case: GeneratedCase) -> dict[str, JsonValue]:
    return {"input": _input_document(case.input), "expected": case.expected.value}


def _input_document(run_input: RunInput) -> dict[str, JsonValue]:
    if isinstance(run_input, FunctionInput):
        return {"arguments": dict(run_input.arguments)}
    return {"ops": list(run_input.ops), "args": [list(args) for args in run_input.args]}


def _case(document: Mapping[str, Any]) -> GeneratedCase:
    stored = document["input"]
    run_input: RunInput
    if "arguments" in stored:
        run_input = FunctionInput(stored["arguments"])
    else:
        run_input = OperationSequence(tuple(stored["ops"]), tuple(map(tuple, stored["args"])))
    return GeneratedCase(run_input, Expected(document["expected"]))
