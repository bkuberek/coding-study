"""What `cstudy ai status` shows: the settings, what each task would use, the keys, the consents
and today's usage (docs/specs/cli.md#cstudy-ai-status)."""

from dataclasses import dataclass
from datetime import date

from coding_study.application.environment import Environment
from coding_study.domain.ai import AiTask, ModelRef, Provider, Routing
from coding_study.domain.ai_records import Consent
from coding_study.domain.ai_routing import (
    TASKS,
    Target,
    TaskRefusedError,
    ready_targets,
    targets_for,
)
from coding_study.domain.ai_usage import UsageCounters, add_up


@dataclass(frozen=True, slots=True)
class TaskStatus:
    task: AiTask
    targets: tuple[Target, ...]
    """The models it sends to, in order; empty while one it needs is unset."""
    ready: bool
    """AI is on, its models are set and their providers have a key."""
    reason: str | None
    """Why it cannot run, as the command words its refusal; None when ready."""
    brief: str | None
    """The reason's first words, for the status line."""


@dataclass(frozen=True, slots=True)
class CredentialsStatus:
    location: str
    keys: frozenset[Provider]
    """Empty when the file does not load."""
    issue: str | None


@dataclass(frozen=True, slots=True)
class TodayStatus:
    day: date
    counters: UsageCounters
    cap: int


@dataclass(frozen=True, slots=True)
class AiStatus:
    enabled: bool
    routing: Routing
    model: ModelRef | None
    fast: ModelRef | None
    strong: ModelRef | None
    tasks: tuple[TaskStatus, ...]
    credentials: CredentialsStatus
    consents: tuple[Consent, ...]
    today: TodayStatus


def ai_status(environment: Environment) -> AiStatus:
    """Reads the config, `credentials.toml`, the consents and today's requests, and sends nothing.
    It works with AI off and with a credentials file that does not load, which it reports."""
    settings = environment.config.ai
    credentials = environment.credentials
    issue = credentials.issue()
    keys = frozenset[Provider]() if issue is not None else credentials.keys_set()
    today = environment.clock.local_date(environment.clock.now())
    return AiStatus(
        settings.enabled,
        settings.routing,
        settings.model,
        settings.fast,
        settings.strong,
        tuple(_task_status(environment, task, keys, issue) for task in TASKS),
        CredentialsStatus(credentials.location, keys, issue),
        environment.ai_store.consents(),
        TodayStatus(
            today,
            add_up(environment.ai_store.calls_between(today, today)),
            settings.daily_token_cap,
        ),
    )


def _task_status(
    environment: Environment, task: AiTask, keys: frozenset[Provider], issue: str | None
) -> TaskStatus:
    settings = environment.config.ai
    try:
        targets = targets_for(task, settings)
    except TaskRefusedError:
        targets = ()
    try:
        ready_targets(task, settings, keys)
    except TaskRefusedError as refusal:
        if issue is not None and settings.enabled and targets:
            return TaskStatus(task, targets, False, issue, issue)
        return TaskStatus(task, targets, False, str(refusal), refusal.brief)
    return TaskStatus(task, targets, True, None, None)
