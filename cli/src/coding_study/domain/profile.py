"""The learner profile: what an entry must match to be listed by default, how a flag widens it,
and the words of the line that says what it hid (docs/specs/cli.md#the-learner-profile,
docs/decisions/0028-learner-profile.md).

Every list the profile applies to calls `Profile.matches`, so the terminal and the page narrow by
one rule. The profile's languages are the workspace's, its roles and domains the user config's.
"""

from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum

from coding_study.domain.config import ProfileSettings
from coding_study.domain.labels import Labels
from coding_study.domain.problem import ALL_LANGUAGES, Language
from coding_study.domain.taxonomy import ANY_ROLE, DOMAINS, PROFILE_JOB_ROLES

LINE_PREFIX = "filtered by your profile:"
LINE_SEPARATOR = " · "


class Dimension(StrEnum):
    """The value is how the profile line names it."""

    LANGUAGES = "languages"
    JOB_ROLES = "roles"
    DOMAINS = "domains"


ALL_DIMENSIONS = tuple(Dimension)
GUIDE_DIMENSIONS = (Dimension.JOB_ROLES, Dimension.DOMAINS)
"""A guide teaches in every language, so `cstudy learn` applies two dimensions."""

PICK_DIMENSIONS = (Dimension.JOB_ROLES, Dimension.DOMAINS)
"""`cstudy next` and `cstudy mock` start a pick in a workspace language, so their languages are
always the workspace's and `--widen` names roles and domains."""

_EVERY_VALUE: dict[Dimension, tuple[str, ...]] = {
    Dimension.LANGUAGES: tuple(ALL_LANGUAGES),
    Dimension.JOB_ROLES: PROFILE_JOB_ROLES,
    Dimension.DOMAINS: DOMAINS,
}

WIDEN_ALL = "all"
WIDEN_DIMENSIONS = {
    "lang": Dimension.LANGUAGES,
    "role": Dimension.JOB_ROLES,
    "domain": Dimension.DOMAINS,
}
"""The `--widen` values that name one dimension; `all` names the three."""


@dataclass(frozen=True, slots=True)
class Widening:
    """The dimensions a run ignores the profile in: `--widen`, and the dimension of each explicit
    `--lang`, `--role` or `--domain`, which replaces the profile there."""

    dimensions: frozenset[Dimension] = frozenset()

    def widens(self, dimension: Dimension) -> bool:
        return dimension in self.dimensions

    def plus(self, *dimensions: Dimension) -> "Widening":
        return Widening(self.dimensions | frozenset(dimensions))


NO_WIDENING = Widening()


def widening_from(
    values: Iterable[str], widenable: Collection[Dimension] = ALL_DIMENSIONS
) -> Widening:
    """The widening of `--widen` values: `lang`, `role`, `domain` or `all`, of those that name a
    dimension of `widenable` (the three, for `cstudy list`; roles and domains for the commands
    whose languages are the workspace's). Any other raises ValueError."""
    names = [name for name, dimension in WIDEN_DIMENSIONS.items() if dimension in widenable]
    dimensions: set[Dimension] = set()
    for value in values:
        if value == WIDEN_ALL:
            dimensions.update(Dimension)
        elif value in names:
            dimensions.add(WIDEN_DIMENSIONS[value])
        else:
            raise ValueError(f'unknown widening "{value}"; use {", ".join(names)} or {WIDEN_ALL}')
    return Widening(frozenset(dimensions))


@dataclass(frozen=True, slots=True)
class NarrowedValues:
    """The values that narrowed a run, by dimension; None where the dimension narrowed nothing."""

    languages: tuple[str, ...] | None = None
    job_roles: tuple[str, ...] | None = None
    domains: tuple[str, ...] | None = None
    """`job_roles` never lists `general`, which matches whatever the profile holds."""

    def phrases(self) -> tuple[str, ...]:
        """`languages python, go`, `roles backend and general`, `domains security`, for the
        dimensions that narrowed."""
        phrases: list[str] = []
        if self.languages is not None:
            phrases.append(f"{Dimension.LANGUAGES} {', '.join(self.languages)}")
        if self.job_roles is not None:
            phrases.append(f"{Dimension.JOB_ROLES} {', '.join(self.job_roles)} and {ANY_ROLE}")
        if self.domains is not None:
            phrases.append(f"{Dimension.DOMAINS} {', '.join(self.domains)}")
        return tuple(phrases)

    @property
    def is_empty(self) -> bool:
        return self.languages is None and self.job_roles is None and self.domains is None


@dataclass(frozen=True, slots=True)
class Profile:
    languages: tuple[Language, ...] = ALL_LANGUAGES
    """The workspace's, in the order of `Language`."""
    job_roles: tuple[str, ...] = PROFILE_JOB_ROLES
    domains: tuple[str, ...] = DOMAINS
    languages_chosen: bool = False
    """The marker lists languages. A marker without them holds all six and chooses none."""

    def values(self, dimension: Dimension) -> tuple[str, ...]:
        match dimension:
            case Dimension.LANGUAGES:
                return tuple(self.languages)
            case Dimension.JOB_ROLES:
                return self.job_roles
            case Dimension.DOMAINS:
                return self.domains

    def narrows(self, dimension: Dimension) -> bool:
        """A dimension narrows when it holds fewer than all its values."""
        return not set(_EVERY_VALUE[dimension]) <= set(self.values(dimension))

    def active(self, applies: Iterable[Dimension], widening: Widening) -> frozenset[Dimension]:
        """The dimensions of `applies` that narrow this run: not widened, and fewer than all."""
        return frozenset(
            dimension
            for dimension in applies
            if not widening.widens(dimension) and self.narrows(dimension)
        )

    def narrowed(
        self, applies: Iterable[Dimension] = ALL_DIMENSIONS, widening: Widening = NO_WIDENING
    ) -> NarrowedValues:
        active = self.active(applies, widening)

        def held(dimension: Dimension) -> tuple[str, ...] | None:
            return self.values(dimension) if dimension in active else None

        return NarrowedValues(
            languages=held(Dimension.LANGUAGES),
            job_roles=held(Dimension.JOB_ROLES),
            domains=held(Dimension.DOMAINS),
        )

    def matches(
        self,
        labels: Labels,
        languages: Collection[Language] = (),
        *,
        applies: Iterable[Dimension] = ALL_DIMENSIONS,
        widening: Widening = NO_WIDENING,
    ) -> bool:
        """Whether an entry with `labels` and the reference `languages` is listed, every active
        dimension matching (docs/specs/cli.md#matching). An entry without the dimension is kept:
        a rubric problem has no languages, and a problem of your own may list no labels."""
        active = self.active(applies, widening)
        checks = (
            Dimension.LANGUAGES not in active
            or not languages
            or any(language in self.languages for language in languages),
            Dimension.JOB_ROLES not in active
            or not labels.job_roles
            or ANY_ROLE in labels.job_roles
            or any(role in self.job_roles for role in labels.job_roles),
            Dimension.DOMAINS not in active
            or not labels.domains
            or any(domain in self.domains for domain in labels.domains),
        )
        return all(checks)


def learner_profile(
    settings: ProfileSettings, workspace_languages: Sequence[Language] | None = None
) -> Profile:
    """The profile of the config's roles and domains and the workspace's languages; None is a
    workspace that has not chosen them (all six)."""
    if workspace_languages is None:
        return Profile(job_roles=settings.job_roles, domains=settings.domains)
    return Profile(
        languages=tuple(language for language in Language if language in workspace_languages),
        job_roles=settings.job_roles,
        domains=settings.domains,
        languages_chosen=True,
    )


@dataclass(frozen=True, slots=True)
class ProfileEffect:
    """What the learner profile did to a listing or a pick's scope: `shown` entries of the `total`
    that `--widen all` would show with the same other filters."""

    narrowed: NarrowedValues
    shown: int
    total: int

    @property
    def hidden(self) -> int:
        return self.total - self.shown


NO_PROFILE_EFFECT = ProfileEffect(NarrowedValues(), 0, 0)
"""A run the profile narrowed nothing in: no count is taken."""


class ProfileLineKind(StrEnum):
    SHOWS = "shows"
    """`cstudy list`: the rows printed of the rows `--widen all` would print."""
    PICKS = "picks"
    """`cstudy next` and `cstudy mock`: the problems in the scope of the pick."""
    SHOWS_THEM = "shows them"
    """`cstudy learn`: two counts, guides and paths."""


@dataclass(frozen=True, slots=True)
class Counted:
    shown: int
    total: int
    noun: str
    """`problems`, `new medium and hard problems`, `guides`, `paths`."""


def profile_line(
    kind: ProfileLineKind, counts: Sequence[Counted], narrowed: NarrowedValues
) -> str | None:
    """The dim line that ends a command's output while the profile hid an entry, or None when
    every count shows all its entries (docs/specs/cli.md#the-profile-line)."""
    if all(count.shown >= count.total for count in counts):
        return None
    counted = ", ".join(f"{count.shown} of {count.total} {count.noun}" for count in counts)
    total = counts[0].total
    match kind:
        case ProfileLineKind.SHOWS:
            lead, tail = counted, f"--widen all shows all {total}"
        case ProfileLineKind.PICKS:
            lead, tail = f"picked from {counted}", f"--widen all picks from all {total}"
        case ProfileLineKind.SHOWS_THEM:
            lead, tail = counted, "--widen all shows them all"
    parts = (lead, *narrowed.phrases(), tail)
    return f"{LINE_PREFIX} {LINE_SEPARATOR.join(parts)}"
