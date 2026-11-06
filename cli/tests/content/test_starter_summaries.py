"""Every catalog problem whose starter is generated has a summary for its header: the `summary` of
its meta.yaml, else the opening of its statement (docs/specs/problem-format.md#starter-header)."""

import pytest
import yaml

from coding_study.adapters.problem_documents import meta_from_document
from coding_study.domain.problem import ProblemKind, StubSource
from coding_study.domain.starter_summary import SUMMARY_LIMIT, starter_summary
from tests.helpers import REPOSITORY_ROOT

SENTENCE_END = (".", "?", "!")


def generated_starters() -> dict[str, str | None]:
    """Problem directory to its starter summary, for the problems that get a generated header."""
    summaries: dict[str, str | None] = {}
    for directory in sorted((REPOSITORY_ROOT / "problems").iterdir()):
        document = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
        meta = meta_from_document(document, f"{directory.name}/meta.yaml")
        if meta.kind is ProblemKind.PROJECT or meta.stub is not StubSource.GENERATED:
            continue
        statement = (directory / "problem.md").read_text(encoding="utf-8")
        summaries[directory.name] = starter_summary(meta, statement)
    return summaries


SUMMARIES = generated_starters()


def test_the_catalog_has_problems_with_generated_starters():
    assert len(SUMMARIES) > 200


@pytest.mark.parametrize(
    "check",
    [
        pytest.param(lambda summary: summary is None, id="empty"),
        pytest.param(lambda summary: len(summary or "") > SUMMARY_LIMIT, id="over the cap"),
        pytest.param(
            lambda summary: summary is not None and not summary.endswith(SENTENCE_END),
            id="cut mid-sentence",
        ),
    ],
)
def test_no_catalog_summary_is(check):
    assert [slug for slug, summary in SUMMARIES.items() if check(summary)] == []
