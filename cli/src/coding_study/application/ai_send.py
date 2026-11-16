"""The one path every request to a provider's model takes: routing, key, cap, consent, request,
usage row (docs/specs/ai.md#routing, #consent and #usage-and-the-daily-token-cap)."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol

from coding_study.application.environment import Environment
from coding_study.domain.ai import AiTask, Provider
from coding_study.domain.ai_models import (
    Ending,
    ModelReply,
    ModelRequest,
    ProviderError,
    ProviderErrorKind,
    Usage,
)
from coding_study.domain.ai_records import CallOutcome, Consent, ModelCall
from coding_study.domain.ai_routing import Target, ready_targets, task_spec
from coding_study.domain.ai_usage import (
    add_up,
    cap_refusal,
    counted_tokens,
    estimate_input_tokens,
    estimate_tokens,
)
from coding_study.domain.errors import UsageError


@dataclass(frozen=True, slots=True)
class SentItem:
    """One thing a request sends, as the consent question lists it."""

    name: str
    """`instructions review-1`, `prompt.md`, `your notes`."""
    size_bytes: int | None = None
    detail: str = ""
    """What more the line says, such as `notes/system-design/url-shortener.md`."""


ReplyCheck = Callable[[ModelReply], None]


@dataclass(frozen=True, slots=True)
class AiPayload:
    """What a task asks of a model."""

    task: AiTask
    instructions: str
    message: str
    items: tuple[SentItem, ...] = ()
    schema: Mapping[str, object] | None = None
    schema_name: str = "reply"
    attempt_id: int | None = None
    """The attempt an AI review reviews, which the usage row records."""
    accept: ReplyCheck | None = None
    """Runs on a complete reply before its usage row is written; raises ProviderError of kind
    `invalid_reply` for a reply the task rejects, which makes the row a failed one with the tokens
    the reply reported."""

    @property
    def text(self) -> str:
        """The request's text, which the estimate counts."""
        return f"{self.instructions}{self.message}"


@dataclass(frozen=True, slots=True)
class ConsentQuestion:
    """What the consent question and the web page's consent document say
    (docs/specs/ai.md#consent)."""

    task: AiTask
    target: Target
    items: tuple[SentItem, ...]
    input_tokens: int
    """The estimate of the request's input."""
    max_output_tokens: int
    today_tokens: int
    """The tokens the cap has counted today."""
    cap: int


class ConsentAsker(Protocol):
    """How an entrypoint gets consent for a model and purpose that has none recorded."""

    def ask(self, question: ConsentQuestion) -> bool:
        """True to send, which records the consent; False for no. Raises UsageError to refuse
        without a question, as a command with no terminal does."""
        ...


@dataclass(frozen=True, slots=True)
class Sent:
    """A request that was answered and passed its check."""

    target: Target
    reply: ModelReply
    call: ModelCall
    """The usage row it wrote."""


@dataclass(frozen=True, slots=True)
class NotSent:
    """The consent question was answered no: nothing was sent and nothing was recorded."""

    target: Target


def available_targets(environment: Environment, task: AiTask) -> tuple[Target, ...]:
    """The models the task sends to: AI is on, each is set and each provider has a key. Raises
    TaskRefusedError (exit code 3) for the first that fails, and ConfigError for a
    `credentials.toml` that does not load."""
    keys = frozenset[Provider]()
    if environment.config.ai.enabled:
        keys = environment.credentials.keys_set()
    return ready_targets(task, environment.config.ai, keys)


def consent_question(
    environment: Environment, target: Target, payload: AiPayload
) -> ConsentQuestion:
    spec = task_spec(payload.task)
    return ConsentQuestion(
        payload.task,
        target,
        payload.items,
        estimate_input_tokens(payload.text),
        spec.max_output_tokens,
        _counted_today(environment),
        environment.config.ai.daily_token_cap,
    )


def send(
    environment: Environment, target: Target, payload: AiPayload, asker: ConsentAsker
) -> Sent | NotSent:
    """Sends the payload to `target`, one of the task's `available_targets`, in the order of
    docs/specs/ai.md: AI on, model set, key, cap, consent, request, usage row.

    A refusal before the request (TaskRefusedError, a cap refusal, a consent the asker refuses)
    raises UsageError and records nothing; a no from the asker returns NotSent. After the
    request a row is written for every outcome: a reply that was cut, refused or rejected by
    `accept`, a ProviderError and Ctrl-C all raise afterwards, the last as KeyboardInterrupt.
    """
    task = payload.task
    spec = task_spec(task)
    if target not in available_targets(environment, task):
        raise ValueError(f"{target.model} is not a model of {task}")
    key = environment.credentials.key(target.model.provider)
    assert key is not None, "available_targets found a key for every provider"
    estimate = estimate_tokens(payload.text, spec.max_output_tokens)
    question = consent_question(environment, target, payload)
    refusal = cap_refusal(task, question.today_tokens, estimate, question.cap)
    if refusal is not None:
        raise UsageError(refusal)
    provider, model_id = target.model.provider, target.model.model_id
    if environment.ai_store.consent(provider, model_id, task) is None:
        if not asker.ask(question):
            return NotSent(target)
        environment.ai_store.grant_consent(
            Consent(provider, model_id, task, environment.clock.now())
        )
    request = ModelRequest(
        target.model,
        payload.instructions,
        payload.message,
        spec.max_output_tokens,
        spec.deadline_s,
        payload.schema,
        payload.schema_name,
    )
    started_at = environment.clock.now()

    def record(
        outcome: CallOutcome, usage: Usage | None, error: ProviderErrorKind | None
    ) -> ModelCall:
        ended_at = environment.clock.now()
        call = ModelCall(
            purpose=task,
            provider=provider,
            model=model_id,
            tier=target.tier,
            attempt_id=payload.attempt_id,
            local_day=environment.clock.local_date(started_at),
            started_at=started_at,
            ended_at=ended_at,
            outcome=outcome,
            error=error,
            input_tokens=usage.input_tokens if usage is not None else None,
            output_tokens=usage.output_tokens if usage is not None else None,
            counted_tokens=counted_tokens(usage, estimate),
            cost_usd=usage.cost_usd if usage is not None else None,
        )
        environment.ai_store.record_call(call)
        return call

    try:
        reply = environment.models.complete(request, key)
    except ProviderError as error:
        record(CallOutcome.FAILED, error.usage, error.kind)
        raise
    except KeyboardInterrupt:
        record(CallOutcome.INTERRUPTED, None, None)
        raise
    failure = _ending_error(reply, target, spec.max_output_tokens)
    if failure is None and payload.accept is not None:
        try:
            payload.accept(reply)
        except ProviderError as error:
            failure = error
    if failure is not None:
        failure.usage = failure.usage or reply.usage
        record(CallOutcome.FAILED, failure.usage, failure.kind)
        raise failure
    return Sent(target, reply, record(CallOutcome.OK, reply.usage, None))


def _ending_error(
    reply: ModelReply, target: Target, max_output_tokens: int
) -> ProviderError | None:
    match reply.ending:
        case Ending.COMPLETE:
            return None
        case Ending.LENGTH:
            return ProviderError(
                ProviderErrorKind.LENGTH,
                f"the reply stopped at its {max_output_tokens:,}-token limit before it was "
                "complete",
                reply.usage,
            )
        case Ending.REFUSED:
            return ProviderError(
                ProviderErrorKind.REFUSED,
                f"{target.model.provider} declined to answer this request",
                reply.usage,
            )


def _counted_today(environment: Environment) -> int:
    today = environment.clock.local_date(environment.clock.now())
    return add_up(environment.ai_store.calls_between(today, today)).counted_tokens
