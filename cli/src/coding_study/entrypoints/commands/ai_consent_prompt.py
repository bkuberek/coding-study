"""The consent question at a terminal (docs/specs/ai.md#consent): the `ConsentAsker` of every
command that sends to a model."""

import sys

import typer

from coding_study.application.ai_consent import consent_needed
from coding_study.application.ai_send import ConsentQuestion, SentItem
from coding_study.domain.ai_routing import sentence_start, task_spec
from coding_study.domain.errors import UsageError

NAME_WIDTH = 30
INDENT = "  "
GAP = "  "
KIB = 1024
PROMPT = "Send it? [y/N] "
YES = frozenset({"y", "yes"})


def stdin_is_terminal() -> bool:
    return sys.stdin.isatty()


class TerminalAsker:
    """Asks `Send it? [y/N]` on standard error and reads one line of standard input. Yes sends;
    no, Enter and end of input do not. Without a terminal it raises UsageError (exit code 3)
    naming `cstudy ai consent`, and asks nothing. Ctrl-C is not caught."""

    def __init__(self, subject: str | None = None) -> None:
        self.subject = subject
        """What the request is about, as `AI review of url-shortener sends`; None for none."""

    def ask(self, question: ConsentQuestion) -> bool:
        if not stdin_is_terminal():
            raise UsageError(consent_needed(question))
        typer.echo(question_text(question, self.subject), err=True)
        typer.echo(PROMPT, nl=False, err=True)
        return sys.stdin.readline().strip().lower() in YES


def question_text(question: ConsentQuestion, subject: str | None = None) -> str:
    """The question's lines, without the `Send it?` prompt."""
    name = task_spec(question.task).name
    provider = question.target.model.provider
    of = f" of {subject}" if subject else ""
    lines = [
        f"{sentence_start(name)}{of} sends, from this machine to {provider}, "
        f"model {question.target.model.model_id}:",
        *_item_lines(question.items),
        f"about {question.input_tokens:,} tokens in and up to {question.max_output_tokens:,} out"
        f" · today {question.today_tokens:,} of {question.cap:,} tokens",
        f"Your {provider} account's terms apply to what it receives. "
        f"cstudy asks once for this model and {name}.",
    ]
    return "\n".join(lines)


def _item_lines(items: tuple[SentItem, ...]) -> list[str]:
    name_width = max([NAME_WIDTH, *(len(item.name) + len(GAP) for item in items)])
    sizes = [_size(item.size_bytes) for item in items]
    size_width = max(map(len, sizes), default=0)
    lines: list[str] = []
    for item, size in zip(items, sizes, strict=True):
        line = f"{INDENT}{item.name.ljust(name_width)}{size.rjust(size_width)}"
        if item.detail:
            line += f"{GAP}{item.detail}"
        lines.append(line.rstrip())
    return lines


def _size(size_bytes: int | None) -> str:
    if size_bytes is None:
        return ""
    if size_bytes < KIB:
        return f"{size_bytes} B"
    return f"{size_bytes / KIB:.1f} KB"
