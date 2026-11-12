"""The closed lists of the catalog (docs/specs/content.md#pattern-taxonomy): the DSA patterns, and
the three labels `domains`, `job_roles` and `scope` (docs/decisions/0020-catalog-labels.md).

The order of `PATTERNS` is the tie-break order of `cstudy next`. schemas/meta.schema.json lists the
same patterns, and both it and schemas/item.schema.json list the same labels as `$defs`; a test
holds each list and its schema equal.
"""

from enum import StrEnum

PATTERNS = (
    "arrays-hashing",
    "two-pointers",
    "sliding-window",
    "stack",
    "monotonic-stack",
    "binary-search",
    "linked-list",
    "trees",
    "tries",
    "heap",
    "backtracking",
    "graphs",
    "topological-sort",
    "advanced-graphs",
    "union-find",
    "dp-1d",
    "dp-2d",
    "greedy",
    "intervals",
    "prefix-sum",
    "math-geometry",
    "bit-manipulation",
    "segment-tree-fenwick",
    "sorting",
    "string-matching",
    "recursion",
)

DOMAINS = (
    "algorithms",
    "backend",
    "security",
    "identity",
    "ai-llm",
    "fintech",
    "data",
    "infrastructure",
    "systems",
    "software-design",
    "frontend",
)
"""What a problem is about; a problem has one or more."""
JOB_ROLES = (
    "general",
    "backend",
    "platform",
    "security-engineer",
    "ai-engineer",
    "ml-engineer",
    "data-engineer",
    "frontend",
)
"""Who a problem is for; a problem has one or more. `general` is any software engineer."""


class Scope(StrEnum):
    """How big the thing you work on is; a problem has exactly one."""

    FUNCTION = "function"
    """One function or class, in one file, with no folder or process of yours."""
    PROJECT = "project"
    """A folder of files."""
    SYSTEM = "system"
    """Several services."""


def pattern_rank(pattern: str) -> int:
    """The taxonomy position; unknown patterns rank after every known one."""
    return PATTERNS.index(pattern) if pattern in PATTERNS else len(PATTERNS)
