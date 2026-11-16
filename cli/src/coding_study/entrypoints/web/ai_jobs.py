"""The checks of the AI jobs, run in the server before their child starts
(docs/specs/web-ui.md#jobs).

Each check is one of the command's own that sends nothing: AI on, the model and key the routing
needs, the cap, and for a review the problem, its attempt, its notes and the mock lock. A refusal
is the CLI's, so a job never starts only to fail. A model without consent for the job's purpose
gets the consent document in a 409 `confirmation_required`; with `confirm` its consent is
recorded and the child, which finds it, asks nothing. The server never sends to a provider.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import assert_never

from coding_study.application.ai_check import check_payload
from coding_study.application.ai_consent import grant
from coding_study.application.ai_models import listing_key
from coding_study.application.ai_review import prepare_review
from coding_study.application.ai_send import (
    AiPayload,
    ConsentQuestion,
    SentItem,
    available_targets,
    cap_checked_question,
)
from coding_study.application.environment import Environment
from coding_study.domain.ai import AiTask, ModelRef
from coding_study.domain.ai_routing import Target, sentence_start, task_spec
from coding_study.domain.cases import JsonValue
from coding_study.entrypoints.web.errors import ApiError, ErrorCode
from coding_study.entrypoints.web.run_options import JobCommand, JobOptions


@dataclass(frozen=True, slots=True)
class _Sending:
    """What a job's child would send, and to which models."""

    payload: AiPayload
    targets: tuple[Target, ...]
    subject: str | None
    """What the request is about, as `AI review of url-shortener`; None for none."""


def check_ai_job(environment: Environment, options: JobOptions) -> None:
    """Raises UsageError, ConfigError and UnknownProblemError as the command would before its
    request, and ApiError `confirmation_required` with the consent document when a model of the
    job has no consent and the request is not confirmed. A confirmed request records the
    consents it would have asked for. Nothing else is recorded and nothing is sent. A job that
    is no AI job passes."""
    match options.command:
        case JobCommand.AI_REVIEW:
            assert options.slug is not None, "the options of ai_review name a problem"
            prepared = prepare_review(environment, options.slug)
            sending = _Sending(prepared.plan.payload, (prepared.target,), prepared.plan.meta.slug)
        case JobCommand.AI_CHECK:
            targets = available_targets(environment, AiTask.CHECK)
            sending = _Sending(check_payload(), targets, None)
        case JobCommand.AI_MODELS:
            assert options.provider is not None, "the options of ai_models name a provider"
            listing_key(environment.config.ai, environment.credentials, options.provider)
            return
        case JobCommand.DOCTOR_FIX | JobCommand.VERIFY | JobCommand.BENCH:
            return
        case _:
            assert_never(options.command)
    _settle_consents(environment, sending, options.confirmed)


def _settle_consents(environment: Environment, sending: _Sending, confirmed: bool) -> None:
    task = sending.payload.task
    questions = [
        cap_checked_question(environment, target, sending.payload) for target in sending.targets
    ]
    lacking = {
        target.model: target
        for target in sending.targets
        if environment.ai_store.consent(target.model.provider, target.model.model_id, task) is None
    }
    if not lacking:
        return
    if confirmed:
        for model in lacking:
            grant(environment, model, task)
        return
    models = tuple(lacking.values())
    raise ApiError(
        ErrorCode.CONFIRMATION_REQUIRED,
        _question(task, sending.subject, [target.model for target in models]),
        {"consent": consent_document(questions[0], models)},
    )


def consent_document(question: ConsentQuestion, models: Iterable[Target]) -> dict[str, JsonValue]:
    """The consent document of a request to `models`, which have no consent: what it sends and
    its size, the estimate, today's tokens against the cap, and the terms that apply."""
    targets = tuple(models)
    providers = dict.fromkeys(target.model.provider for target in targets)
    return {
        "purpose": question.task.value,
        "models": [_model_document(target) for target in targets],
        "sends": [_item_document(item) for item in question.items],
        "input_tokens": question.input_tokens,
        "output_tokens": question.max_output_tokens,
        "today": {"tokens": question.today_tokens, "cap": question.cap},
        "terms": " ".join(
            f"Your {provider} account's terms apply to what it receives." for provider in providers
        ),
    }


def _model_document(target: Target) -> dict[str, JsonValue]:
    tier = None if target.tier is None else target.tier.value
    return {
        "tier": tier,
        "provider": target.model.provider.value,
        "model": target.model.model_id,
    }


def _item_document(item: SentItem) -> dict[str, JsonValue]:
    label = f"{item.name}, {item.detail}" if item.detail else item.name
    return {"label": label, "bytes": item.size_bytes}


def _question(task: AiTask, subject: str | None, models: list[ModelRef]) -> str:
    name = sentence_start(task_spec(task).name)
    to = " and ".join(str(model) for model in models)
    match task:
        case AiTask.REVIEW:
            return f"{name}{f' of {subject}' if subject else ''} sends your notes to {to}. Send it?"
        case AiTask.CHECK:
            return f"{name} sends a fixed test message to {to}. Send it?"
        case _:
            assert_never(task)
