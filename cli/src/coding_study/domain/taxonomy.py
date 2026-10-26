"""The DSA pattern taxonomy (docs/specs/content.md#pattern-taxonomy).

Its order is the tie-break order of `cstudy next`; schemas/meta.schema.json lists the same ids.
"""

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
)


def pattern_rank(pattern: str) -> int:
    """The taxonomy position; unknown patterns rank after every known one."""
    return PATTERNS.index(pattern) if pattern in PATTERNS else len(PATTERNS)
