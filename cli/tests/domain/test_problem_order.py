"""The order of `cstudy list` (docs/specs/compatibility.md#order)."""

from dataclasses import replace

from coding_study.domain.problem import (
    ComparatorSpec,
    ComparatorType,
    ContentStatus,
    Difficulty,
    ProblemKind,
    ProblemMeta,
    Track,
)
from coding_study.domain.signature import FunctionSignature, Returns
from coding_study.domain.type_dsl import Scalar, ScalarType

BASE = ProblemMeta(
    slug="two-sum",
    title="Two Sum",
    status=ContentStatus.READY,
    difficulty=Difficulty.EASY,
    track=Track.DSA,
    kind=ProblemKind.FUNCTION,
    signature=FunctionSignature("twoSum", (), Returns(ScalarType(Scalar.INT))),
    comparator=ComparatorSpec(ComparatorType.EXACT),
    approaches=(),
    patterns=("arrays-hashing",),
)


def listed(*metas: ProblemMeta) -> list[str]:
    return [meta.slug for meta in sorted(metas, key=lambda meta: meta.listing_key())]


def meta(slug: str, **fields: object) -> ProblemMeta:
    return replace(BASE, slug=slug, **fields)  # type: ignore[arg-type]


def test_the_catalog_lists_before_your_own_problems_whatever_their_slug():
    assert listed(meta("aardvark", workspace=True), meta("zebra")) == ["zebra", "aardvark"]


def test_tracks_list_in_track_order():
    debugging = meta("alpha", track=Track.DEBUGGING)
    lld = meta("beta", track=Track.LLD)
    practical = meta("gamma", track=Track.PRACTICAL)
    dsa = meta("delta")
    assert listed(debugging, lld, practical, dsa) == ["delta", "gamma", "beta", "alpha"]


def test_a_track_lists_by_the_taxonomy_position_of_the_primary_pattern():
    trees = meta("alpha", patterns=("trees", "arrays-hashing"))
    hashing = meta("beta", patterns=("arrays-hashing", "trees"))
    stack = meta("gamma", patterns=("stack",))
    assert listed(trees, hashing, stack) == ["beta", "gamma", "alpha"]


def test_problems_without_patterns_list_first_in_their_track():
    plain = meta("zebra", track=Track.PRACTICAL, patterns=())
    patterned = meta("alpha", track=Track.PRACTICAL, patterns=("arrays-hashing",))
    assert listed(patterned, plain) == ["zebra", "alpha"]


def test_the_curriculum_order_comes_before_the_slug():
    late = meta("alpha", order=2)
    early = meta("beta", order=1)
    assert listed(late, early) == ["beta", "alpha"]


def test_the_slug_makes_the_order_total():
    assert listed(meta("beta"), meta("alpha")) == ["alpha", "beta"]
