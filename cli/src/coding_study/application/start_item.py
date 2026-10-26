"""`cstudy start` for a non-autograded item: notes from the template, the prompt, an attempt.

Specs: docs/specs/cli.md#cstudy-start and content.md#non-autograded-item-format. Item attempts have
no language; `stub_path` holds the notes file. Like stubs, the notes are kept on resume and
archived for `--fresh` and review attempts.
"""

from dataclasses import dataclass, replace

from coding_study.application.environment import Environment
from coding_study.application.item_statement_file import guide_links, write_item_statement
from coding_study.application.start_attempt import attempt_mode
from coding_study.domain import layout
from coding_study.domain.attempts import Attempt, AttemptMode, AttemptStatus, NewAttempt
from coding_study.domain.errors import ContentError, ContentIssue
from coding_study.domain.item_statement import notes_text
from coding_study.domain.items import TEMPLATE_FILE, GuideLink, ItemMeta


@dataclass(frozen=True, slots=True)
class ItemStartRequest:
    slug: str
    fresh: bool = False
    timer_s: int | None = None
    mock: bool = False
    """Started by `cstudy mock`: a new attempt gets mode `mock`."""


@dataclass(frozen=True, slots=True)
class StartedItem:
    meta: ItemMeta
    attempt: Attempt
    notes_path: str
    statement_path: str
    resumed: bool
    created_notes: bool
    archived_to: str | None = None
    guides: tuple[GuideLink, ...] = ()
    """The study guides found under the user's study-guides root."""


def start_item_attempt(environment: Environment, request: ItemStartRequest) -> StartedItem:
    meta = environment.items.load(request.slug)
    guides = guide_links(environment, meta)
    statement = write_item_statement(environment, meta, guides)
    in_progress = environment.progress.active_attempt(meta.slug)
    if in_progress is not None and not request.fresh:
        notes = _Notes(environment, meta)
        created = notes.ensure(notes.template())
        return StartedItem(meta, in_progress, notes.path, statement, True, created, guides=guides)
    return replace(_ItemStart(environment, meta, request).begin(in_progress), guides=guides)


class _ItemStart:
    """A new attempt, archiving the previous notes for `--fresh` and review attempts."""

    def __init__(self, environment: Environment, meta: ItemMeta, request: ItemStartRequest) -> None:
        self._environment = environment
        self._meta = meta
        self._request = request
        self._notes = _Notes(environment, meta)

    def begin(self, in_progress: Attempt | None) -> StartedItem:
        progress, clock, slug = self._environment.progress, self._environment.clock, self._meta.slug
        mode = attempt_mode(self._request.mock, progress.schedule_entry(slug) is not None)
        template = self._notes.template()
        previous = progress.latest_attempt(slug, None)
        if in_progress is not None:
            abandoned = replace(in_progress, status=AttemptStatus.ABANDONED, ended_at=clock.now())
            progress.update_attempt(abandoned)
        attempt = progress.add_attempt(
            NewAttempt(slug, None, mode, clock.now(), self._request.timer_s, self._notes.path)
        )
        replaces_notes = self._request.fresh or mode is AttemptMode.REVIEW
        archived_to = self._notes.archive((previous or attempt).id) if replaces_notes else None
        if archived_to is not None:
            attempt = replace(attempt, archive_path=archived_to)
            progress.update_attempt(attempt)
        created = self._notes.ensure(template)
        statement = layout.statement_path(slug)
        return StartedItem(
            self._meta, attempt, self._notes.path, statement, False, created, archived_to
        )


class _Notes:
    """The user's notes file for one item."""

    def __init__(self, environment: Environment, meta: ItemMeta) -> None:
        self._environment = environment
        self._meta = meta
        self.path = layout.notes_path(meta)

    def template(self) -> str:
        """The notes a new attempt starts from; raises ContentError without template.md."""
        text = self._environment.items.read_text(self._meta.slug, TEMPLATE_FILE)
        if text is None:
            directory = self._environment.items.item_directory(self._meta.slug)
            raise ContentError([ContentIssue(f"{directory}/{TEMPLATE_FILE}", "", "missing")])
        return notes_text(self._meta, text)

    def ensure(self, text: str) -> bool:
        """Writes `text` when the notes file is missing; True when it did."""
        workspace = self._environment.workspace
        if workspace.exists(self.path):
            return False
        workspace.write_text(self.path, text)
        return True

    def archive(self, owner_id: int) -> str | None:
        """Moves existing notes into the archive directory of the attempt that wrote them."""
        if not self._environment.workspace.exists(self.path):
            return None
        directory = layout.notes_archive_directory(self._meta.slug, owner_id)
        return self._environment.workspace.move_into(self.path, directory)
