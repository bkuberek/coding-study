"""The check: `check-1` sent to each model the routing names, so the key, the model id and
structured output are each seen working (docs/specs/ai.md#the-check)."""

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from enum import StrEnum

from coding_study.application.ai_send import (
    AiPayload,
    ConsentAsker,
    NotSent,
    SentItem,
    send,
)
from coding_study.application.environment import Environment
from coding_study.domain.ai import AiTask
from coding_study.domain.ai_models import ModelReply, ProviderError, ProviderErrorKind, Usage
from coding_study.domain.ai_routing import (
    CHECK_INSTRUCTIONS,
    CHECK_MESSAGE,
    CHECK_SCHEMA,
    CHECK_VERSION,
    Target,
    check_passed,
)

SCHEMA_NAME = "check"


class CheckOutcome(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    NOT_SENT = "not_sent"
    """The consent question was answered no."""


@dataclass(frozen=True, slots=True)
class CheckResult:
    """What the check of one model found."""

    target: Target
    outcome: CheckOutcome
    seconds: float | None = None
    """From the request's start to its end; None unless the check passed."""
    usage: Usage | None = None
    """What the provider reported for a passed check."""
    error: str | None = None
    """Why a failed check failed, as the provider error words it."""


def check_payload() -> AiPayload:
    """The request every model of the check gets."""
    return AiPayload(
        AiTask.CHECK,
        CHECK_INSTRUCTIONS,
        CHECK_MESSAGE,
        (
            SentItem(f"instructions {CHECK_VERSION}", len(CHECK_INSTRUCTIONS.encode())),
            SentItem("a fixed test message", len(CHECK_MESSAGE.encode())),
            SentItem("nothing of yours"),
        ),
        CHECK_SCHEMA,
        SCHEMA_NAME,
        accept=_require_ok,
    )


def run_check(
    environment: Environment, targets: Sequence[Target], asker: ConsentAsker
) -> Iterator[CheckResult]:
    """Checks each of `targets`, the check's `available_targets`, in order, yielding each result
    as it finishes. A model that fails does not stop the next. A refusal before a request (the
    cap, a consent the asker refuses) raises UsageError; Ctrl-C stores its row and re-raises."""
    payload = check_payload()
    for target in targets:
        try:
            sent = send(environment, target, payload, asker)
        except ProviderError as error:
            yield CheckResult(target, CheckOutcome.FAILED, error=str(error))
            continue
        if isinstance(sent, NotSent):
            yield CheckResult(target, CheckOutcome.NOT_SENT)
            continue
        seconds = (sent.call.ended_at - sent.call.started_at).total_seconds()
        yield CheckResult(target, CheckOutcome.PASSED, seconds, sent.reply.usage)


def _require_ok(reply: ModelReply) -> None:
    if not check_passed(reply.data):
        raise ProviderError(
            ProviderErrorKind.INVALID_REPLY,
            'the model\'s reply did not follow the check format: it is not {"ok": true}',
        )
