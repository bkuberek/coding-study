"""AI review of a rubric problem's notes: what a review sends, the refusals before it, the dry run,
the stored record, and the list, show and dismiss of stored reviews (docs/specs/ai.md#ai-review).

A review runs in two steps so an entrypoint can say what it is about to do: `prepare_review`
applies every refusal and names the model, `run_review` sends. Nothing is stored for a refusal, a
no at the consent question, the dry run, or a reply that fails its checks (which leaves a failed
request row and no review).
"""

import hashlib
import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from coding_study.application.ai_send import (
    AiPayload,
    ConsentAsker,
    NotSent,
    Sent,
    SentItem,
    available_targets,
    send,
)
from coding_study.application.environment import Environment
from coding_study.application.item_statement_file import item_change
from coding_study.application.mock_interview import require_no_running_mock
from coding_study.application.past_attempt_files import FilesSource, past_attempt_files
from coding_study.application.practice_catalog import catalog_slugs, is_item
from coding_study.domain import layout
from coding_study.domain.ai import AiTask
from coding_study.domain.ai_models import ModelReply, ProviderError, ProviderErrorKind
from coding_study.domain.ai_records import ModelCall, ReviewRecord
from coding_study.domain.ai_review import (
    INSTRUCTIONS,
    PROMPT_VERSION,
    REVIEW_SCHEMA,
    REVIEW_SCHEMA_NAME,
    CheckedReply,
    NumberedCriterion,
    check_reply,
    numbered_criteria,
    review_message,
    review_record,
)
from coding_study.domain.ai_routing import Target, TaskRefusedError, targets_for, task_spec
from coding_study.domain.ai_usage import estimate_input_tokens
from coding_study.domain.attempts import Attempt, AttemptStatus
from coding_study.domain.errors import ContentError, ContentIssue, UnknownProblemError, UsageError
from coding_study.domain.items import PROMPT_FILE, ItemMeta
from coding_study.domain.problem_files import RUBRIC_FILE
from coding_study.domain.rubric import parse_rubric

COMMAND = "cstudy ai review"
MAX_NOTES_BYTES = 64 * 1024
"""The most of the notes a review reads."""
_KIB = 1024
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_HEADING = re.compile(r"\s{0,3}#{1,6}(?:\s|$)")


@dataclass(frozen=True, slots=True)
class ReviewPlan:
    """What a review of one attempt's notes sends, once no refusal applies."""

    meta: ItemMeta
    attempt: Attempt
    notes_path: str
    notes: str
    """The notes as they are on disk, which the request sends."""
    notes_sha256: str
    rubric_sha256: str
    criteria: tuple[NumberedCriterion, ...]
    payload: AiPayload
    """The request: its instructions and message are the text of the dry run."""


@dataclass(frozen=True, slots=True)
class DryRun:
    """What a review would send and where, with nothing sent and nothing recorded."""

    plan: ReviewPlan
    targets: tuple[Target, ...]
    """The model the review would use; empty when the config leaves it unset."""
    unset: str | None
    """Why `targets` is empty: the message of the setting that is missing."""
    input_tokens: int
    """The estimate of the request's input."""
    max_output_tokens: int


@dataclass(frozen=True, slots=True)
class PreparedReview:
    """A review no refusal stops: the plan and the model it goes to."""

    plan: ReviewPlan
    target: Target


@dataclass(frozen=True, slots=True)
class ReviewView:
    """A stored review with the problem it belongs to."""

    slug: str
    record: ReviewRecord
    notes_changed: bool | None
    """Whether the attempt's notes differ now from the notes reviewed; None when they are gone."""


@dataclass(frozen=True, slots=True)
class Reviewed:
    """A review that was sent, checked and stored."""

    review: ReviewView
    target: Target
    call: ModelCall
    """The usage row of its request."""


@dataclass(frozen=True, slots=True)
class ReviewList:
    slug: str
    reviews: tuple[ReviewView, ...]
    """Newest first, dismissed ones included."""


@dataclass(frozen=True, slots=True)
class Dismissal:
    review: ReviewView
    already_dismissed: bool


def plan_review(environment: Environment, slug: str | None) -> ReviewPlan:
    """The review of the notes of `slug`'s attempt in progress, else of its latest attempt;
    `slug` defaults to the problem of the active attempt.

    Raises UsageError (exit code 3) for a problem checked by tests, no attempt, notes that are
    missing, still the template or over 64 KiB, and a running mock interview, in that order; and
    UnknownProblemError for a slug no problem has.
    """
    meta = _rubric_problem(environment, slug)
    attempt = _reviewed_attempt(environment, meta.slug)
    notes_path = layout.notes_path(meta)
    raw = _read_notes(environment, notes_path)
    notes = raw.decode("utf-8", errors="replace")
    if _nothing_written(notes):
        raise UsageError(
            f"your notes are still the template: write your answer in {notes_path} first"
        )
    if len(raw) > MAX_NOTES_BYTES:
        raise UsageError(
            f"your notes are {-(-len(raw) // _KIB)} KiB; AI review reads at most "
            f"{MAX_NOTES_BYTES // _KIB} KiB"
        )
    require_no_running_mock(environment, COMMAND)
    rubric = _rubric_text(environment, meta)
    criteria = numbered_criteria(parse_rubric(rubric))
    prompt = environment.items.read_text(meta.slug, PROMPT_FILE)
    change = item_change(environment, meta)
    message = review_message(
        title=meta.title, prompt=prompt or "", change=change, criteria=criteria, notes=notes
    )
    items = [
        SentItem(f"instructions {PROMPT_VERSION}", _size(INSTRUCTIONS)),
        *([SentItem("prompt.md", _size(prompt))] if prompt is not None else []),
        *([SentItem("change.diff", _size(change.diff))] if change.diff is not None else []),
        *(SentItem(f"files/{file.name}", _size(file.text)) for file in change.files),
        SentItem(f"rubric.md, {len(criteria)} criteria", _size(_criteria_text(criteria))),
        SentItem("your notes", len(raw), notes_path),
    ]

    def accept(reply: ModelReply) -> None:
        _checked(reply, criteria, notes)

    payload = AiPayload(
        AiTask.REVIEW,
        INSTRUCTIONS,
        message,
        tuple(items),
        REVIEW_SCHEMA,
        REVIEW_SCHEMA_NAME,
        attempt.id,
        accept,
    )
    return ReviewPlan(
        meta, attempt, notes_path, notes, _sha256(raw), _sha256(rubric.encode()), criteria, payload
    )


def dry_run_review(environment: Environment, slug: str | None) -> DryRun:
    """The text a review would send and the model it would send to. It needs no key and no
    consent, with AI on or off; the refusals about the notes and the mock interview apply."""
    plan = plan_review(environment, slug)
    spec = task_spec(AiTask.REVIEW)
    targets: tuple[Target, ...] = ()
    unset: str | None = None
    try:
        targets = targets_for(AiTask.REVIEW, environment.config.ai)
    except TaskRefusedError as refused:
        unset = str(refused)
    return DryRun(
        plan, targets, unset, estimate_input_tokens(plan.payload.text), spec.max_output_tokens
    )


def prepare_review(environment: Environment, slug: str | None) -> PreparedReview:
    """Every refusal before a request: those of `plan_review`, then AI off, a model unset and a
    provider without a key (TaskRefusedError), all UsageError."""
    plan = plan_review(environment, slug)
    (target,) = available_targets(environment, AiTask.REVIEW)
    return PreparedReview(plan, target)


def run_review(
    environment: Environment, prepared: PreparedReview, asker: ConsentAsker
) -> Reviewed | NotSent:
    """Sends the prepared review through `ai_send.send` and stores the review its reply makes.

    Raises UsageError for the cap and a consent the asker refuses, and ProviderError for a
    failed request or a reply that fails its checks, which stores no review; Ctrl-C raises
    KeyboardInterrupt after its request row is written. A no from the asker returns NotSent.
    """
    plan = prepared.plan
    sent = send(environment, prepared.target, plan.payload, asker)
    if not isinstance(sent, Sent):
        return sent
    checked = _checked(sent.reply, plan.criteria, plan.notes)
    model = prepared.target.model
    record = review_record(
        attempt_id=plan.attempt.id,
        created_at=environment.clock.now(),
        model=model,
        rubric_sha256=plan.rubric_sha256,
        notes_sha256=plan.notes_sha256,
        checked=checked,
        usage=sent.reply.usage,
    )
    review_id = environment.ai_store.add_review(record)
    return Reviewed(show_review(environment, review_id), prepared.target, sent.call)


def list_reviews(environment: Environment, slug: str | None) -> ReviewList:
    """The reviews of `slug`'s attempts, newest first; `slug` defaults to the problem of the
    active attempt. Works with AI off and during a mock interview."""
    meta = _rubric_problem(environment, slug)
    records = environment.ai_store.reviews_of_problem(meta.slug)
    return ReviewList(meta.slug, tuple(_view(environment, record) for record in records))


def show_review(environment: Environment, review_id: int) -> ReviewView:
    """Raises UsageError for an id no review has."""
    return _view(environment, _stored(environment, review_id))


def dismiss_review(environment: Environment, review_id: int) -> Dismissal:
    """Marks the review dismissed; it stays stored. Dismissing it again changes nothing. Raises
    UsageError for an id no review has."""
    _stored(environment, review_id)
    changed = environment.ai_store.dismiss_review(review_id, environment.clock.now())
    return Dismissal(show_review(environment, review_id), already_dismissed=not changed)


def notes_changed(environment: Environment, record: ReviewRecord) -> bool | None:
    """Whether the attempt's notes differ now from the notes the review read: its notes file, or
    the copy a later attempt's start archived. None when they are gone."""
    attempt = environment.progress.attempt(record.attempt_id)
    if attempt is None:
        return None
    current = _attempt_notes(environment, attempt)
    return None if current is None else _sha256(current) != record.notes_sha256


def _rubric_problem(environment: Environment, slug: str | None) -> ItemMeta:
    if slug is None:
        active = environment.progress.active_attempt()
        if active is None:
            raise UsageError("no attempt in progress; start one with cstudy start <slug>")
        slug = active.slug
    if not is_item(environment, slug):
        if slug not in catalog_slugs(environment):
            raise UnknownProblemError(slug)
        raise UsageError(
            f"{slug} is checked by tests; AI review is for rubric problems "
            "(system-design and code-review)"
        )
    return environment.items.load(slug)


def _reviewed_attempt(environment: Environment, slug: str) -> Attempt:
    progress = environment.progress
    attempt = progress.active_attempt(slug) or progress.latest_attempt(slug, None)
    if attempt is None:
        raise UsageError(f"no attempt of {slug} yet: start it with cstudy start {slug}")
    return attempt


def _read_notes(environment: Environment, notes_path: str) -> bytes:
    folder, name = _split(notes_path)
    try:
        return environment.workspace.read_within(folder, name)
    except FileNotFoundError:
        raise UsageError(f"{notes_path} is missing: AI review reads your notes") from None
    except ValueError as error:
        raise UsageError(f"cannot read {notes_path}: {error}") from None


def _attempt_notes(environment: Environment, attempt: Attempt) -> bytes | None:
    """The notes of `attempt` where they are now; None when they are gone or unreadable."""
    path = layout.notes_path(environment.items.attempted(attempt.slug))
    folder, name = _split(path)
    if attempt.status is not AttemptStatus.IN_PROGRESS:
        found = past_attempt_files(environment, attempt.id)
        if found.source is FilesSource.MISSING or found.root is None:
            return None
        folder = found.root
    try:
        return environment.workspace.read_within(folder, name)
    except (FileNotFoundError, ValueError):
        return None


def _split(path: str) -> tuple[str, str]:
    location = PurePosixPath(path)
    return location.parent.as_posix(), location.name


def _nothing_written(notes: str) -> bool:
    """Whether nothing is left of the notes once HTML comments, headings and blank space are
    taken out."""
    lines = _COMMENT.sub("", notes).splitlines()
    return not any(line.strip() and not _HEADING.match(line) for line in lines)


def _rubric_text(environment: Environment, meta: ItemMeta) -> str:
    text = environment.items.read_text(meta.slug, RUBRIC_FILE)
    if text is None:
        directory = environment.items.item_directory(meta.slug)
        raise ContentError([ContentIssue(f"{directory}/{RUBRIC_FILE}", "", "missing")])
    return text


def _checked(
    reply: ModelReply, criteria: tuple[NumberedCriterion, ...], notes: str
) -> CheckedReply:
    """Raises ProviderError of kind `invalid_reply`, carrying the reply's usage, for a reply that
    does not follow the review format."""
    if reply.data is None:
        raise ProviderError(
            ProviderErrorKind.INVALID_REPLY,
            "the model's reply did not follow the review format: it is not a JSON object; "
            "nothing was stored",
            reply.usage,
        )
    return check_reply(reply.data, criteria, notes, reply.usage)


def _criteria_text(criteria: tuple[NumberedCriterion, ...]) -> str:
    return "\n".join(f"{criterion.id}. {criterion.text}" for criterion in criteria)


def _size(text: str) -> int:
    return len(text.encode())


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _stored(environment: Environment, review_id: int) -> ReviewRecord:
    record = environment.ai_store.review(review_id)
    if record is None:
        raise UsageError(f"no AI review {review_id}")
    return record


def _view(environment: Environment, record: ReviewRecord) -> ReviewView:
    attempt = environment.progress.attempt(record.attempt_id)
    assert attempt is not None, "a review's attempt is stored with it"
    return ReviewView(attempt.slug, record, notes_changed(environment, record))
