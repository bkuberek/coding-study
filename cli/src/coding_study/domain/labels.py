"""The labels of a catalog entry and the filter over them (docs/decisions/0020-catalog-labels.md).

A problem or an item says what it is about (`domains`), who it is for (`job_roles`) and how big the
thing you work on is (`scope`). The values come from `coding_study.domain.taxonomy`.
"""

from dataclasses import dataclass

from coding_study.domain.taxonomy import Scope


@dataclass(frozen=True, slots=True)
class Labels:
    """Empty only on a workspace problem, which may leave the labels out (check S24)."""

    domains: tuple[str, ...] = ()
    job_roles: tuple[str, ...] = ()
    scope: Scope | None = None


@dataclass(frozen=True, slots=True)
class LabelFilter:
    """`--domain`, `--role` and `--scope`: every set field must match. Each is one value, and
    `domain` and `role` match any of the listed values."""

    domain: str | None = None
    role: str | None = None
    scope: Scope | None = None

    @property
    def is_set(self) -> bool:
        return any(value is not None for value in (self.domain, self.role, self.scope))

    def matches(self, labels: Labels) -> bool:
        checks = (
            self.domain is None or self.domain in labels.domains,
            self.role is None or self.role in labels.job_roles,
            self.scope in (None, labels.scope),
        )
        return all(checks)
