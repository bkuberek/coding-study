"""`cstudy ai check` and `cstudy ai models` (docs/specs/cli.md#cstudy-ai-check and
#cstudy-ai-models). `models` needs no workspace."""

from collections.abc import Sequence
from pathlib import Path
from typing import Annotated

import typer
from rich.text import Text

from coding_study.adapters.environment_factory import load_ai_access, load_environment
from coding_study.application.ai_check import CheckOutcome, CheckResult, run_check
from coding_study.application.ai_keys import parse_provider
from coding_study.application.ai_models import list_provider_models
from coding_study.application.ai_send import available_targets
from coding_study.domain.ai import AiTask
from coding_study.domain.ai_routing import Target
from coding_study.entrypoints.commands.ai_consent_prompt import TerminalAsker
from coding_study.entrypoints.commands.ai_report import SEPARATOR, dollars
from coding_study.entrypoints.shared import ExitCode, command_environ, console

PROVIDER_HELP = "anthropic, google, openai or openrouter."
TIER_GAP = 2
MODEL_GAP = 3
FAILED = "FAIL"


def check(context: typer.Context) -> None:
    """Send a fixed test request to each model the routing names and show whether it answered."""
    environment = load_environment(Path.cwd(), command_environ(context), Path.home())
    targets = available_targets(environment, AiTask.CHECK)
    output = console(context)
    tier_width = max((len(str(target.tier)) for target in targets if target.tier), default=0)
    model_width = max(len(str(target.model)) for target in targets)
    failed = False
    for result in run_check(environment, targets, TerminalAsker()):
        failed = failed or result.outcome is CheckOutcome.FAILED
        output.print(Text(_line(result, tier_width, model_width)))
    if failed:
        raise typer.Exit(ExitCode.ENVIRONMENT_ERROR)


def models(
    context: typer.Context,
    provider: Annotated[str, typer.Argument(help=PROVIDER_HELP)],
) -> None:
    """List the model ids a provider offers, for ai.model, ai.fast and ai.strong."""
    chosen = parse_provider(provider)
    access = load_ai_access(Path.cwd(), command_environ(context), Path.home())
    output = console(context)
    for model_id in list_provider_models(
        access.settings, access.credentials, access.models, chosen
    ):
        output.print(Text(model_id))


def _line(result: CheckResult, tier_width: int, model_width: int) -> str:
    tier = _tier(result.target, tier_width)
    model = str(result.target.model).ljust(model_width + MODEL_GAP)
    return f"{tier}{model}{_verdict(result)}".rstrip()


def _tier(target: Target, width: int) -> str:
    if not width:
        return ""
    return (str(target.tier) if target.tier else "").ljust(width + TIER_GAP)


def _verdict(result: CheckResult) -> str:
    match result.outcome:
        case CheckOutcome.FAILED:
            return f"{FAILED} {result.error}"
        case CheckOutcome.NOT_SENT:
            return "not sent"
        case CheckOutcome.PASSED:
            assert result.seconds is not None
            return SEPARATOR.join(["ok", f"{result.seconds:.1f} s", *_usage_parts(result)])


def _usage_parts(result: CheckResult) -> Sequence[str]:
    usage = result.usage
    if usage is None:
        return ["tokens unknown", "cost unknown"]
    cost = "cost unknown" if usage.cost_usd is None else dollars(usage.cost_usd)
    return [f"{usage.total_tokens:,} tokens", cost]
