"""Canonical content IDs, `<type>/<slug>` (docs/specs/compatibility.md#canonical-content-ids)."""

from enum import StrEnum

from coding_study.domain.problem import SLUG_PATTERN


class ContentType(StrEnum):
    PROBLEM = "problem"
    GUIDE = "guide"
    PATH = "path"
    DOC = "doc"
    """A page of the user docs."""


SEPARATOR = "/"
_TYPES = ", ".join(ContentType)


def content_id(content_type: ContentType, slug: str) -> str:
    """`problem/two-sum`: the type and the slug, which the caller got from content."""
    return f"{content_type}{SEPARATOR}{slug}"


def parse_content_id(text: str) -> tuple[ContentType, str]:
    """The type and the slug of an ID; raises ValueError for text that is not `<type>/<slug>` with
    a known type and a slug."""
    type_name, separator, slug = text.partition(SEPARATOR)
    try:
        content_type = ContentType(type_name)
    except ValueError:
        raise ValueError(f"not a content ID: {text!r}; the type is one of {_TYPES}") from None
    if not separator or not SLUG_PATTERN.fullmatch(slug):
        raise ValueError(f"not a content ID: {text!r}; expected {content_type}{SEPARATOR}<slug>")
    return content_type, slug
