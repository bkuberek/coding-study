"""Consent to send to a provider's model for a purpose (docs/specs/ai.md#consent)."""

from coding_study.application.ai_send import ConsentQuestion
from coding_study.application.environment import Environment
from coding_study.domain.ai import AiTask, ModelRef
from coding_study.domain.ai_records import Consent
from coding_study.domain.ai_routing import sentence_start, task_spec
from coding_study.domain.errors import UsageError


def parse_model(text: str) -> ModelRef:
    """Raises UsageError for text that is not `<provider>:<model id>`."""
    try:
        return ModelRef.parse(text)
    except ValueError as error:
        raise UsageError(f'"{text}" is not a model: {error}') from None


def parse_purpose(text: str) -> AiTask:
    """Raises UsageError for a purpose that is none of `review` and `check`."""
    try:
        return AiTask(text)
    except ValueError:
        known = ", ".join(AiTask)
        raise UsageError(f'unknown purpose "{text}"; use one of {known}') from None


def grant(environment: Environment, model: ModelRef, purpose: AiTask) -> Consent:
    """Records the consent, which needs no key and works with AI off; a consent already recorded
    keeps its day."""
    stored = environment.ai_store.consent(model.provider, model.model_id, purpose)
    if stored is not None:
        return stored
    consent = Consent(model.provider, model.model_id, purpose, environment.clock.now())
    environment.ai_store.grant_consent(consent)
    return consent


def revoke(environment: Environment, model: ModelRef, purpose: AiTask) -> bool:
    """False when there was no consent to revoke."""
    return environment.ai_store.revoke_consent(model.provider, model.model_id, purpose)


def consent_needed(question: ConsentQuestion) -> str:
    """What a run with no terminal says when the request has no consent."""
    target = question.target.model
    return (
        f"{sentence_start(task_spec(question.task).name)} needs your consent to send to {target}: "
        f"run it once at a terminal, or cstudy ai consent {target} --purpose {question.task}"
    )


class RefusingAsker:
    """The asker of a run with no terminal, or of one whose consents were recorded beforehand: a
    request without consent is refused with exit code 3, and nothing is sent."""

    def ask(self, question: ConsentQuestion) -> bool:
        raise UsageError(consent_needed(question))
