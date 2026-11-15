"""Reading the canonical IDs of a `--json` document or a web API response."""

from typing import Any

from coding_study.domain.content_ids import ContentType, parse_content_id


def content_ids_in(document: Any) -> list[tuple[ContentType, str]]:
    """The type and the slug of every object of `document` that has a `slug`, in document order.

    Fails for an object whose `id` is missing or is not the canonical ID of its `slug`."""
    found: list[tuple[ContentType, str]] = []
    if isinstance(document, dict):
        if "slug" in document:
            assert "id" in document, f"{document['slug']} has no id"
            content_type, slug = parse_content_id(document["id"])
            assert slug == document["slug"], f"{document['id']} is not the id of {document['slug']}"
            found.append((content_type, slug))
        for value in document.values():
            found += content_ids_in(value)
    elif isinstance(document, list):
        for value in document:
            found += content_ids_in(value)
    return found
