"""What the web UI's page does over HTTP, for the slow tests that drive a real `cstudy serve`
(docs/specs/web-ui.md#endpoints): log in, start and finish attempts, start runs, read their
streams and cancel them."""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field

import httpx2

from tests.scripted_runs import Frame, read_frames
from tests.serve_process import RunningServer

RUN_SECONDS = 240
"""Generous: the machine running the slow tests is often loaded."""


@dataclass
class Page:
    """A logged-in page: its client, the headers of its writes, and the attempt it last started
    or found in progress, by slug."""

    client: httpx2.Client
    headers: dict[str, str]
    attempts: dict[str, int] = field(default_factory=dict[str, int])

    def start_attempt(self, slug: str, language: str | None) -> httpx2.Response:
        """The Start dialog's request, as `cstudy start <slug> --lang <language> --no-open`."""
        body = {"slug": slug, "language": language, "fresh": False, "timer_minutes": None}
        response = self.client.post("/api/v1/attempts", json=body, headers=self.headers)
        if response.status_code == 201:
            self.attempts[slug] = response.json()["attempt_id"]
        return response

    def status(self, slug: str) -> httpx2.Response:
        return self.client.get(f"/api/v1/attempts/{self.attempts[slug]}")

    def finish(self, slug: str, body: Mapping[str, object]) -> httpx2.Response:
        """The Done dialog's request, as `cstudy done`."""
        path = f"/api/v1/attempts/{self.attempts[slug]}/done"
        return self.client.post(path, json=dict(body), headers=self.headers)

    def start(self, slug: str, command: str = "test") -> httpx2.Response:
        body = {"attempt_id": self.attempts[slug], "command": command}
        return self.client.post("/api/v1/runs", json=body, headers=self.headers)

    def started(self, slug: str, command: str = "test") -> str:
        response = self.start(slug, command)
        assert response.status_code == 201, response.text
        return response.json()["id"]

    def stream(self, run_id: str) -> Iterator[Frame]:
        path = f"/api/v1/runs/{run_id}/events"
        with self.client.stream("GET", path, timeout=RUN_SECONDS) as response:
            yield from read_frames(response.iter_lines())

    def played(self, run_id: str) -> list[Frame]:
        return list(self.stream(run_id))

    def cancel(self, run_id: str) -> httpx2.Response:
        return self.client.post(f"/api/v1/runs/{run_id}/cancel", headers=self.headers)


def opened_page(server: RunningServer) -> Page:
    """A page logged in with the printed URL, knowing the attempts in progress."""
    server.wait_until_listening()
    client = httpx2.Client(base_url=server.address, timeout=RUN_SECONDS)
    client.get(server.login_url)
    csrf = client.get("/").text.split('name="cstudy-csrf" content="')[1].split('"')[0]
    page = Page(client, {"Origin": server.address, "X-Cstudy-CSRF": csrf})
    for entry in client.get("/api/v1/problems").json()["entries"]:
        if entry["in_progress"]:
            page.attempts[entry["slug"]] = entry["in_progress"][0]["attempt_id"]
    return page
