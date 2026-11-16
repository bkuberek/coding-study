"""Which model each AI task uses, and when a task is refused before anything is sent
(docs/specs/ai.md#routing)."""

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from coding_study.domain.ai import AI_OFF, AiTask, ModelRef, Provider, Routing, Tier
from coding_study.domain.config import AiSettings
from coding_study.domain.errors import UsageError

CHECK_VERSION = "check-1"
CHECK_INSTRUCTIONS = (
    "You answer a connection test from a command-line tool. "
    'Reply with the JSON object {"ok": true} and nothing else.'
)
CHECK_MESSAGE = 'Reply with {"ok": true}.'
CHECK_SCHEMA: Mapping[str, object] = MappingProxyType(
    {
        "type": "object",
        "additionalProperties": False,
        "required": ["ok"],
        "properties": {"ok": {"type": "boolean"}},
    }
)
"""The reply the check asks for, in the portable subset of docs/specs/ai.md#providers."""


def check_passed(data: Mapping[str, object] | None) -> bool:
    """Whether a check's reply is `{"ok": true}`."""
    return data is not None and len(data) == 1 and data.get("ok") is True


@dataclass(frozen=True, slots=True)
class TaskSpec:
    """One row of the task table."""

    task: AiTask
    name: str
    """How a message names the task mid-sentence: `AI review`, `the check`."""
    noun: str
    """`review`, `check`: for `this review needs up to 18,800`."""
    tiers: tuple[Tier, ...]
    """The tiers auto routing sends to, in order."""
    max_output_tokens: int
    deadline_s: float
    """For each model the task sends to."""


TASKS: Mapping[AiTask, TaskSpec] = MappingProxyType(
    {
        AiTask.REVIEW: TaskSpec(AiTask.REVIEW, "AI review", "review", (Tier.STRONG,), 16_000, 300),
        AiTask.CHECK: TaskSpec(
            AiTask.CHECK, "the check", "check", (Tier.FAST, Tier.STRONG), 1_000, 60
        ),
    }
)


def task_spec(task: AiTask) -> TaskSpec:
    return TASKS[task]


def sentence_start(text: str) -> str:
    """`text` with its first letter capitalized: `the check` becomes `The check`."""
    return text[:1].upper() + text[1:]


@dataclass(frozen=True, slots=True)
class Target:
    """A model a task sends to, and the tier that chose it (None under fixed routing)."""

    tier: Tier | None
    model: ModelRef


class TaskRefusedError(UsageError):
    """A task refused before anything is sent (exit code 3)."""

    def __init__(self, message: str, brief: str) -> None:
        super().__init__(message)
        self.brief = brief
        """The message's first words, as `cstudy ai status` shows a task that cannot run."""


def _setting(settings: AiSettings, tier: Tier) -> ModelRef | None:
    return settings.fast if tier is Tier.FAST else settings.strong


def targets_for(task: AiTask, settings: AiSettings) -> tuple[Target, ...]:
    """The models the task sends to, in order, without regard to whether AI is on. Raises
    TaskRefusedError for a model the task needs and the config leaves unset."""
    spec = task_spec(task)
    if settings.routing is Routing.FIXED:
        if settings.model is None:
            raise TaskRefusedError(
                "ai.model is not set: choose the model of fixed routing in Settings or with "
                "cstudy config edit",
                "ai.model is not set",
            )
        return (Target(None, settings.model),)
    targets: list[Target] = []
    for tier in spec.tiers:
        model = _setting(settings, tier)
        if model is None:
            raise TaskRefusedError(
                f"ai.{tier} is not set: auto routing serves {spec.name} from the {tier} tier",
                f"ai.{tier} is not set",
            )
        if all(target.model != model for target in targets):
            targets.append(Target(tier, model))
    return tuple(targets)


def ready_targets(
    task: AiTask, settings: AiSettings, keys: Collection[Provider]
) -> tuple[Target, ...]:
    """The models the task sends to, once AI is on, each model is set and each provider has a key.
    Raises TaskRefusedError for the first that fails, in that order."""
    if not settings.enabled:
        raise TaskRefusedError(AI_OFF, "AI is off")
    targets = targets_for(task, settings)
    for target in targets:
        provider = target.model.provider
        if provider not in keys:
            used_by = f"the {target.tier} tier" if target.tier is not None else "ai.model"
            raise TaskRefusedError(
                f"no key for {provider}, which {used_by} uses: cstudy ai key {provider}, "
                "or Settings",
                f"no key for {provider}",
            )
    return targets
