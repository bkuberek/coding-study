"""What `cstudy stats` reports (docs/specs/progress-and-scheduling.md#statistics).

Groups cover the `ready` problems and items, the content `cstudy next` can pick, so a group's
weakness equals the score `cstudy next` uses for it. `since` only narrows the attempt columns and
the finished count; problems, mastery, weakness, reviews and the streak always describe today.
"""

import statistics
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum
from fractions import Fraction

from coding_study.domain.attempts import Grade
from coding_study.domain.bench_verdict import Verdict
from coding_study.domain.next_selection import Candidate
from coding_study.domain.problem import ContentStatus, Difficulty, Language, Track
from coding_study.domain.weakness import RECENT_ATTEMPTS, GradedAttempt, GroupHistory

CADENCE_DAYS = 7
"""The practice cadence KPI counts finished attempts per week (docs/prd.md)."""


class StatsGrouping(StrEnum):
    PATTERN = "pattern"
    """The `cstudy next` group: the primary pattern of a `dsa` problem, else the track."""
    TRACK = "track"
    LANG = "lang"
    DIFFICULTY = "difficulty"


@dataclass(frozen=True, slots=True)
class StatsAttempt:
    """A finished (`passed` or `failed`) attempt."""

    id: int
    slug: str
    language: Language | None
    passed: bool
    grade: Grade
    started_at: datetime
    ended_at: datetime
    ended_on: date
    """The local calendar date of `ended_at`."""

    @property
    def solve_time(self) -> timedelta:
        return self.ended_at - self.started_at

    def graded(self) -> GradedAttempt:
        return GradedAttempt(self.id, self.slug, self.grade, self.ended_at, self.ended_on)


@dataclass(frozen=True, slots=True)
class LatestBench:
    """The latest bench of the user's code (not `--refs-only`) of one problem in one language."""

    slug: str
    language: Language
    verdict: Verdict
    ran_at: datetime


@dataclass(frozen=True, slots=True)
class BenchGrade:
    """The verdict of the latest user bench of one problem in one language."""

    slug: str
    language: Language
    verdict: Verdict
    ran_on: date
    """The local calendar date of the run."""


@dataclass(frozen=True, slots=True)
class StatsQuery:
    today: date
    grouping: StatsGrouping = StatsGrouping.PATTERN
    since: date | None = None
    """Attempts and bench runs that ended before this local date are left out."""


@dataclass(frozen=True, slots=True)
class GroupStats:
    name: str
    problems: int
    attempted: int
    """Problems with a finished attempt."""
    passed: int
    """Problems with a passed attempt."""
    mastered: int
    recent_attempts: int
    """The last 10 finished attempts, or fewer."""
    recent_passed: int
    median_solve: timedelta | None
    """Over passed attempts; None without any."""
    weakness: Fraction

    @property
    def pass_rate(self) -> Fraction | None:
        if not self.recent_attempts:
            return None
        return Fraction(self.recent_passed, self.recent_attempts)


@dataclass(frozen=True, slots=True)
class ProgressStats:
    groups: tuple[GroupStats, ...]
    finished: int
    """Every finished attempt, also of slugs outside the content (removed or draft)."""
    last_7_days: int
    streak_days: int
    due_today: int
    overdue: int
    bench: Mapping[Verdict, int]
    """Every verdict, with 0 for verdicts no latest bench has."""

    @property
    def benched(self) -> int:
        return sum(self.bench.values())


def progress_stats(
    entries: Sequence[Candidate],
    attempts: Sequence[StatsAttempt],
    bench: Sequence[BenchGrade],
    query: StatsQuery,
) -> ProgressStats:
    ready = [entry for entry in entries if entry.content is ContentStatus.READY]
    days = {attempt.ended_on for attempt in attempts}
    week_start = query.today - timedelta(days=CADENCE_DAYS - 1)
    return ProgressStats(
        groups=_Groups(ready, attempts, query).stats(),
        finished=sum(1 for attempt in attempts if _since(attempt.ended_on, query.since)),
        last_7_days=sum(1 for attempt in attempts if week_start <= attempt.ended_on),
        streak_days=streak_days(days, query.today),
        due_today=sum(1 for entry in ready if _due_on(entry) == query.today),
        overdue=sum(1 for entry in ready if (_due_on(entry) or query.today) < query.today),
        bench=_bench_counts(grade for grade in bench if _since(grade.ran_on, query.since)),
    )


def streak_days(days: set[date], today: date) -> int:
    """Consecutive days with a finished attempt, ending today, or yesterday while today has
    none yet."""
    day = today if today in days else today - timedelta(days=1)
    streak = 0
    while day in days:
        streak += 1
        day -= timedelta(days=1)
    return streak


def _since(day: date, since: date | None) -> bool:
    return since is None or day >= since


def _due_on(entry: Candidate) -> date | None:
    schedule = entry.progress.schedule
    return schedule.due_on if schedule else None


def _bench_counts(grades: Iterable[BenchGrade]) -> dict[Verdict, int]:
    counts = dict.fromkeys(Verdict, 0)
    for grade in grades:
        counts[grade.verdict] += 1
    return counts


type _Rank = tuple[int, int, str]


class _Groups:
    def __init__(
        self, entries: Sequence[Candidate], attempts: Sequence[StatsAttempt], query: StatsQuery
    ) -> None:
        self._query = query
        self._keys = _GROUP_KEYS[query.grouping]
        self._members: dict[str, list[Candidate]] = {}
        self._ranks: dict[str, _Rank] = {}
        for entry in entries:
            for name, rank in self._keys(entry):
                self._members.setdefault(name, []).append(entry)
                self._ranks[name] = rank
        by_slug = {entry.slug: entry for entry in entries}
        self._attempts: dict[str, list[StatsAttempt]] = {}
        for attempt in attempts:
            entry = by_slug.get(attempt.slug)
            if entry is not None:
                for name in self._attempt_groups(entry, attempt):
                    self._attempts.setdefault(name, []).append(attempt)

    def stats(self) -> tuple[GroupStats, ...]:
        names = sorted(self._members, key=self._ranks.__getitem__)
        return tuple(self._group(name) for name in names)

    def _attempt_groups(self, entry: Candidate, attempt: StatsAttempt) -> list[str]:
        if self._query.grouping is not StatsGrouping.LANG:
            return [name for name, _ in self._keys(entry)]
        language = attempt.language
        if language is None or language not in entry.languages:
            return []
        return [language.value]

    def _group(self, name: str) -> GroupStats:
        members = self._members[name]
        every_attempt = self._attempts.get(name, [])
        attempts = [found for found in every_attempt if _since(found.ended_on, self._query.since)]
        recent = sorted(attempts, key=_recency, reverse=True)[:RECENT_ATTEMPTS]
        passed = [found for found in attempts if found.passed]
        mastered = self._mastered(members, every_attempt)
        history = GroupHistory(len(members), mastered, [found.graded() for found in every_attempt])
        return GroupStats(
            name=name,
            problems=len(members),
            attempted=len({found.slug for found in attempts}),
            passed=len({found.slug for found in passed}),
            mastered=mastered,
            recent_attempts=len(recent),
            recent_passed=sum(1 for found in recent if found.passed),
            median_solve=_median([found.solve_time for found in passed]),
            weakness=history.weakness(self._query.today),
        )

    def _mastered(self, members: Sequence[Candidate], attempts: Sequence[StatsAttempt]) -> int:
        """By language: mastered problems count where they were passed in the language."""
        mastered = [entry for entry in members if entry.progress.is_mastered]
        if self._query.grouping is not StatsGrouping.LANG:
            return len(mastered)
        passed = {attempt.slug for attempt in attempts if attempt.passed}
        return sum(1 for entry in mastered if entry.slug in passed)


def _recency(attempt: StatsAttempt) -> tuple[datetime, int]:
    return attempt.ended_at, attempt.id


def _median(durations: Sequence[timedelta]) -> timedelta | None:
    if not durations:
        return None
    return timedelta(seconds=statistics.median(found.total_seconds() for found in durations))


def _by_pattern(entry: Candidate) -> list[tuple[str, _Rank]]:
    group = entry.group
    return [(group.name, group.tie_break_key())]


def _by_track(entry: Candidate) -> list[tuple[str, _Rank]]:
    return [(entry.track.value, _enum_rank(_TRACKS, entry.track))]


def _by_difficulty(entry: Candidate) -> list[tuple[str, _Rank]]:
    return [(entry.difficulty.value, _enum_rank(_DIFFICULTIES, entry.difficulty))]


def _by_language(entry: Candidate) -> list[tuple[str, _Rank]]:
    """Items have no language, so they belong to no group."""
    if not entry.autograded:
        return []
    return [(language.value, _enum_rank(_LANGUAGES, language)) for language in entry.languages]


def _enum_rank[T](members: tuple[T, ...], member: T) -> _Rank:
    return members.index(member), 0, ""


_TRACKS = tuple(Track)
_DIFFICULTIES = tuple(Difficulty)
_LANGUAGES = tuple(Language)
_GROUP_KEYS: Mapping[StatsGrouping, Callable[[Candidate], list[tuple[str, _Rank]]]] = {
    StatsGrouping.PATTERN: _by_pattern,
    StatsGrouping.TRACK: _by_track,
    StatsGrouping.DIFFICULTY: _by_difficulty,
    StatsGrouping.LANG: _by_language,
}
