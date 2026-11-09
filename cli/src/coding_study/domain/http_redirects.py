"""What a browser sends after a redirect, for a step that follows them
(docs/specs/service-projects.md#multi-step-cases)."""

from dataclasses import replace
from urllib.parse import urljoin

from coding_study.domain.http_case import HttpRequest
from coding_study.domain.http_grading import HttpResponse
from coding_study.domain.http_origins import split_url

MAX_REDIRECTS = 10
"""More hops than any login takes; past them the last redirect is the step's answer."""
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
REPEATING_STATUSES = frozenset({307, 308})
"""These repeat the request as it was; the others turn it into a GET with no body."""
LOCATION = "location"
GET = "GET"


def redirected(request: HttpRequest, response: HttpResponse, url: str) -> HttpRequest | None:
    """The next request, or None when `response` is no redirect, or names no URL the grader can
    send. `url` is where `request` went, which a relative `Location` is read against. A GET carries
    none of the step's headers: only its jar's cookies go along, as a browser's would."""
    location = response.headers.get(LOCATION)
    if response.status not in REDIRECT_STATUSES or not location:
        return None
    split = split_url(urljoin(url, location))
    if split is None:
        return None
    origin, path = split
    if response.status in REPEATING_STATUSES:
        return replace(request, path=path, query={}, origin=origin)
    return HttpRequest(GET, path, origin=origin, jar=request.jar, follow_redirects=True)
