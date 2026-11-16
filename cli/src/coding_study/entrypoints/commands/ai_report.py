"""How `cstudy ai status` and `cstudy ai usage` show their reports: lines for a terminal and the
`--json` documents (docs/specs/cli.md#cstudy-ai-status and #cstudy-ai-usage)."""

from collections.abc import Callable, Iterator, Sequence
from datetime import date, datetime
from pathlib import Path

from coding_study.application.ai_status import AiStatus, TaskStatus, TodayStatus
from coding_study.application.ai_usage import UsageReport
from coding_study.domain.ai import Provider, Routing
from coding_study.domain.ai_records import Consent
from coding_study.domain.ai_usage import UsageCounters
from coding_study.domain.cases import JsonValue

LABEL_WIDTH = 10
SEPARATOR = " · "
NO_VALUE = "-"
COLUMN_GAP = "  "
COST_DECIMALS = 6
MIN_COST_DECIMALS = 2
JSON_COST_DECIMALS = 10
AI_OFF_LINE = (
    "off: nothing is sent; turn it on with ai.enabled = true (cstudy config edit) or in Settings"
)
HOME = "~"
_USAGE_HEADERS = ("DAY", "PROVIDER", "MODEL", "PURPOSE", "REQUESTS", "INPUT", "OUTPUT", "COST")
_RIGHT_ALIGNED = frozenset({"REQUESTS", "INPUT", "OUTPUT"})


def status_lines(
    status: AiStatus, local_date: Callable[[datetime], date], home: Path
) -> Iterator[str]:
    yield _labeled("ai", _ai_text(status))
    for task in status.tasks:
        yield _labeled(task.task, _task_text(task))
    yield _labeled("keys", _keys_text(status, home))
    yield _labeled("consents", _consents_text(status.consents, local_date))
    yield _labeled("today", _today_text(status.today))


def status_document(status: AiStatus) -> dict[str, JsonValue]:
    keys: dict[str, JsonValue] = {
        provider.value: provider in status.credentials.keys for provider in Provider
    }
    return {
        "enabled": status.enabled,
        "routing": status.routing.value,
        "models": {
            "model": _model_or_none(status.model),
            "fast": _model_or_none(status.fast),
            "strong": _model_or_none(status.strong),
        },
        "tasks": [_task_document(task) for task in status.tasks],
        "credentials": {
            "path": status.credentials.location,
            "keys": keys,
            "issue": status.credentials.issue,
        },
        "consents": [_consent_document(consent) for consent in status.consents],
        "today": {
            "day": status.today.day.isoformat(),
            "tokens": status.today.counters.counted_tokens,
            "cap": status.today.cap,
            "requests": status.today.counters.requests,
            "cost_usd": _cost_value(status.today.counters.cost_usd),
            "requests_without_cost": status.today.counters.requests_without_cost,
        },
    }


def usage_lines(report: UsageReport) -> Iterator[str]:
    if not report.rows:
        span = "the last day" if report.days == 1 else f"the last {report.days} days"
        yield f"no AI requests in {span}"
        return
    table = [
        (
            row.day.isoformat(),
            row.provider.value,
            row.model,
            row.purpose.value,
            f"{row.counters.requests:,}",
            f"{row.counters.input_tokens:,}",
            f"{row.counters.output_tokens:,}",
            _cost_cell(row.counters),
        )
        for row in report.rows
    ]
    widths = [
        max(len(header), *(len(row[column]) for row in table))
        for column, header in enumerate(_USAGE_HEADERS)
    ]
    yield _usage_row(_USAGE_HEADERS, widths)
    for row in table:
        yield _usage_row(row, widths)
    total = report.total
    yield (
        f"{'total'.ljust(widths[0])}{COLUMN_GAP}"
        f"{_requests(total.requests)}, {total.failed:,} failed{SEPARATOR}"
        f"{total.counted_tokens:,} tokens counted{SEPARATOR}{_cost_text(total)}"
    )


def usage_document(report: UsageReport) -> dict[str, JsonValue]:
    return {
        "days": report.days,
        "from": report.first.isoformat(),
        "to": report.last.isoformat(),
        "cap": report.cap,
        "rows": [
            {
                "day": row.day.isoformat(),
                "provider": row.provider.value,
                "model": row.model,
                "purpose": row.purpose.value,
                **_counters_document(row.counters),
            }
            for row in report.rows
        ],
        "total": _counters_document(report.total),
    }


def shown_path(location: str, home: Path) -> str:
    """The path with the home directory written as `~`."""
    path = Path(location)
    return f"{HOME}/{path.relative_to(home).as_posix()}" if path.is_relative_to(home) else location


def _labeled(label: str, text: str) -> str:
    return f"{label.ljust(LABEL_WIDTH)}{text}"


def _ai_text(status: AiStatus) -> str:
    if not status.enabled:
        return AI_OFF_LINE
    parts = ["on", f"routing {status.routing}"]
    if status.routing is Routing.FIXED:
        parts.append(str(status.model) if status.model is not None else "model not set")
    else:
        parts.append(f"fast {status.fast}" if status.fast is not None else "fast not set")
        parts.append(f"strong {status.strong}" if status.strong is not None else "strong not set")
    return SEPARATOR.join(parts)


def _task_text(task: TaskStatus) -> str:
    if not task.ready:
        return task.brief or ""
    models = ", ".join(
        f"{target.tier} {target.model}" if target.tier is not None else str(target.model)
        for target in task.targets
    )
    return f"ready{SEPARATOR}{models}"


def _keys_text(status: AiStatus, home: Path) -> str:
    credentials = status.credentials
    if credentials.issue is not None:
        return credentials.issue
    names = [provider.value for provider in Provider if provider in credentials.keys]
    return f"{', '.join(names) or 'none'}{SEPARATOR}in {shown_path(credentials.location, home)}"


def _consents_text(consents: Sequence[Consent], local_date: Callable[[datetime], date]) -> str:
    if not consents:
        return "none"
    return SEPARATOR.join(
        f"{consent.provider}:{consent.model} {consent.purpose} "
        f"({local_date(consent.granted_at).isoformat()})"
        for consent in consents
    )


def _today_text(today: TodayStatus) -> str:
    counters = today.counters
    text = f"{counters.counted_tokens:,} of {today.cap:,} tokens{SEPARATOR}"
    text += _requests(counters.requests)
    if counters.requests:
        text += f"{SEPARATOR}{_cost_text(counters)}"
    return text


def _requests(count: int) -> str:
    return f"{count:,} request" if count == 1 else f"{count:,} requests"


def _cost_text(counters: UsageCounters) -> str:
    if counters.cost_usd is None:
        return "cost unknown"
    text = f"{_dollars(counters.cost_usd)} known"
    if counters.requests_without_cost:
        text += f", {_requests(counters.requests_without_cost)} without a reported cost"
    return text


def _cost_cell(counters: UsageCounters) -> str:
    return NO_VALUE if counters.cost_usd is None else _dollars(counters.cost_usd)


def _dollars(amount: float) -> str:
    """`$0.00003`: up to six decimals, at least two."""
    digits = f"{amount:.{COST_DECIMALS}f}".rstrip("0")
    whole, _, fraction = digits.partition(".")
    return f"${whole}.{fraction.ljust(MIN_COST_DECIMALS, '0')}"


def _usage_row(cells: Sequence[str], widths: Sequence[int]) -> str:
    aligned = [
        cell.rjust(width) if header in _RIGHT_ALIGNED else cell.ljust(width)
        for cell, width, header in zip(cells, widths, _USAGE_HEADERS, strict=True)
    ]
    return COLUMN_GAP.join(aligned).rstrip()


def _model_or_none(model: object) -> str | None:
    return None if model is None else str(model)


def _task_document(task: TaskStatus) -> dict[str, JsonValue]:
    return {
        "task": task.task.value,
        "models": [
            {
                "tier": target.tier.value if target.tier is not None else None,
                "model": str(target.model),
            }
            for target in task.targets
        ],
        "ready": task.ready,
        "reason": task.reason,
    }


def _consent_document(consent: Consent) -> dict[str, JsonValue]:
    return {
        "provider": consent.provider.value,
        "model": consent.model,
        "purpose": consent.purpose.value,
        "granted_at": consent.granted_at.isoformat(),
    }


def _counters_document(counters: UsageCounters) -> dict[str, JsonValue]:
    return {
        "requests": counters.requests,
        "failed": counters.failed,
        "input_tokens": counters.input_tokens,
        "output_tokens": counters.output_tokens,
        "counted_tokens": counters.counted_tokens,
        "cost_usd": _cost_value(counters.cost_usd),
        "requests_without_cost": counters.requests_without_cost,
    }


def _cost_value(cost: float | None) -> float | None:
    return None if cost is None else round(cost, JSON_COST_DECIMALS)
