"""How `cstudy ai review` shows its results: the review's lines, the list, the dry run and the
`--json` documents (docs/specs/cli.md#cstudy-ai-review, docs/specs/ai.md#what-it-shows).

Text a model wrote is shown as text: control characters are dropped here again, and callers print
it as `rich.text.Text`, which never reads markup."""

import unicodedata
from collections.abc import Callable, Iterator, Sequence
from datetime import date, datetime

from coding_study.application.ai_review import DryRun, ReviewList, ReviewView
from coding_study.domain.ai_records import ReviewItem, Verdict
from coding_study.domain.ai_review import PROMPT_VERSION, VerdictCounts, count_verdicts
from coding_study.domain.cases import JsonValue
from coding_study.domain.content_ids import ContentType, content_id
from coding_study.entrypoints.commands.ai_report import (
    COLUMN_GAP,
    JSON_COST_DECIMALS,
    SEPARATOR,
    dollars,
)

NOTICE = "The same answer can get a different review. It changes no grade and no schedule."
NOTES_CHANGED = "notes changed since this review"
DISMISSED = "dismissed"
VERDICT_LABELS = {Verdict.MET: "met", Verdict.PARTIAL: "partly", Verdict.MISSING: "missed"}
VERDICT_WIDTH = 9
"""A criterion's verdict, padded; what follows it and the lines under it start after it."""
_INDENT = " " * (2 + VERDICT_WIDTH)
_LIST_HEADERS = ("REVIEW", "ATTEMPT", "WHEN", "MODEL", "RESULT")
_RIGHT_ALIGNED = frozenset({"REVIEW", "ATTEMPT"})
_RULE = "==="
_LABEL_WIDTH = 9

LocalDate = Callable[[datetime], date]


def review_lines(view: ReviewView) -> Iterator[str]:
    record = view.record
    yield SEPARATOR.join(
        (
            "AI review",
            _plain(view.slug),
            f"attempt {record.attempt_id}",
            f"{record.provider}:{_plain(record.model)}",
            _plain(record.prompt_version),
        )
    )
    yield NOTICE
    if view.notes_changed:
        yield NOTES_CHANGED
    if record.dismissed_at is not None:
        yield DISMISSED
    area: str | None = None
    for item in record.items:
        if item.area != area:
            area = item.area
            yield ""
            yield _plain(item.area)
        yield from _criterion_lines(item)
    yield ""
    yield from _block(_labeled("summary", ""), " " * _LABEL_WIDTH, record.summary)
    yield _labeled(
        "result",
        SEPARATOR.join(
            (
                result_text(count_verdicts(record.items)),
                _tokens_text(record.input_tokens, record.output_tokens),
                _cost_text(record.cost_usd),
            )
        ),
    )


def list_lines(listing: ReviewList, local_date: LocalDate) -> Iterator[str]:
    if not listing.reviews:
        yield f"no AI reviews of {_plain(listing.slug)} yet"
        return
    table: list[tuple[str, ...]] = []
    for view in listing.reviews:
        record = view.record
        result = result_text(count_verdicts(record.items))
        if record.dismissed_at is not None:
            result += f"{SEPARATOR}{DISMISSED}"
        table.append(
            (
                str(record.id),
                str(record.attempt_id),
                local_date(record.created_at).isoformat(),
                f"{record.provider}:{_plain(record.model)}",
                result,
            )
        )
    widths = [
        max(len(header), *(len(row[column]) for row in table))
        for column, header in enumerate(_LIST_HEADERS)
    ]
    yield _list_row(_LIST_HEADERS, widths)
    for row in table:
        yield _list_row(row, widths)


def dry_run_text(dry: DryRun) -> str:
    """The instructions and the message as a review sends them, framed, then the model and the
    estimate."""
    payload = dry.plan.payload
    model = (
        ", ".join(str(target.model) for target in dry.targets)
        if dry.targets
        else dry.unset or "not set"
    )
    return "".join(
        (
            f"{_RULE} instructions {PROMPT_VERSION} {_RULE}\n",
            _ending_with_newline(payload.instructions),
            f"{_RULE} message {_RULE}\n",
            _ending_with_newline(payload.message),
            f"{_RULE} not sent {_RULE}\n",
            f"{_labeled('model', model)}\n",
            _labeled(
                "estimate",
                f"about {dry.input_tokens:,} tokens in and up to {dry.max_output_tokens:,} out",
            ),
            "\n",
        )
    )


def review_document(view: ReviewView) -> dict[str, JsonValue]:
    record = view.record
    assert record.id is not None, "a stored review has its id"
    counts = count_verdicts(record.items)
    return {
        "id": content_id(ContentType.PROBLEM, view.slug),
        "slug": view.slug,
        "review_id": record.id,
        "attempt_id": record.attempt_id,
        "format": record.format,
        "created_at": record.created_at.isoformat(),
        "provider": record.provider.value,
        "model": record.model,
        "prompt_version": record.prompt_version,
        "rubric_sha256": record.rubric_sha256,
        "notes_sha256": record.notes_sha256,
        "notes_changed": view.notes_changed,
        "criteria": [_criterion_document(item) for item in record.items],
        "summary": record.summary,
        "counts": {
            "met": counts.met,
            "partial": counts.partial,
            "missing": counts.missing,
            "total": counts.total,
        },
        "quotes_dropped": record.quotes_dropped,
        "usage": {
            "input_tokens": record.input_tokens,
            "output_tokens": record.output_tokens,
            "cost_usd": None
            if record.cost_usd is None
            else round(record.cost_usd, JSON_COST_DECIMALS),
        },
        "dismissed_at": None if record.dismissed_at is None else record.dismissed_at.isoformat(),
    }


def list_document(listing: ReviewList) -> dict[str, JsonValue]:
    return {
        "id": content_id(ContentType.PROBLEM, listing.slug),
        "slug": listing.slug,
        "reviews": [review_document(view) for view in listing.reviews],
    }


def result_text(counts: VerdictCounts) -> str:
    """`18 met · 6 partly · 4 missed of 28`."""
    return (
        f"{counts.met} met{SEPARATOR}{counts.partial} partly{SEPARATOR}"
        f"{counts.missing} missed of {counts.total}"
    )


def _criterion_lines(item: ReviewItem) -> Iterator[str]:
    label = VERDICT_LABELS[item.verdict]
    yield from _block(f"  {label.ljust(VERDICT_WIDTH)}", _INDENT, item.criterion)
    for quote in item.evidence:
        yield from _block(f'{_INDENT}"', _INDENT, f'{quote}"')
    if item.gaps.strip():
        yield from _block(f"{_INDENT}gap: ", _INDENT + " " * len("gap: "), item.gaps)


def _criterion_document(item: ReviewItem) -> dict[str, JsonValue]:
    return {
        "number": item.number,
        "area": item.area,
        "criterion": item.criterion,
        "verdict": item.verdict.value,
        "evidence": list(item.evidence),
        "gaps": item.gaps,
    }


def _block(first: str, rest: str, text: str) -> Iterator[str]:
    """`text` as lines, the first after `first` and the others after `rest`."""
    lines = [_plain(line) for line in text.splitlines()] or [""]
    yield f"{first}{lines[0]}".rstrip()
    for line in lines[1:]:
        yield f"{rest}{line}".rstrip()


def _plain(text: str) -> str:
    """`text` without control characters."""
    return "".join(char for char in text if unicodedata.category(char) != "Cc")


def _labeled(label: str, text: str) -> str:
    return f"{label.ljust(_LABEL_WIDTH)}{text}"


def _tokens_text(input_tokens: int | None, output_tokens: int | None) -> str:
    if input_tokens is None or output_tokens is None:
        return "tokens not reported"
    return f"{input_tokens:,} tokens in, {output_tokens:,} out"


def _cost_text(cost: float | None) -> str:
    return "cost unknown" if cost is None else dollars(cost)


def _list_row(cells: Sequence[str], widths: Sequence[int]) -> str:
    aligned = [
        cell.rjust(width) if header in _RIGHT_ALIGNED else cell.ljust(width)
        for cell, width, header in zip(cells, widths, _LIST_HEADERS, strict=True)
    ]
    return COLUMN_GAP.join(aligned).rstrip()


def _ending_with_newline(text: str) -> str:
    return text if text.endswith("\n") else f"{text}\n"
