"""`GET /`, the page, and `GET /assets/{path}`, the built front end
(docs/specs/web-ui.md#session-and-preferences).

The page is `page.html` with this response's CSRF token and CSP nonce filled in. The assets are
exactly the files `static/manifest.json` lists: nothing else in the directory is served.
"""

import re
from pathlib import Path

from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, Response
from starlette.routing import BaseRoute, Route

from coding_study.adapters.serve_install import manifest_digests
from coding_study.entrypoints.web.security import (
    NO_STORE,
    PAGE_PATH,
    content_security_policy,
    new_nonce,
)

PAGE_TEMPLATE = Path(__file__).parent / "page.html"
CSRF_SLOT = "{{csrf}}"
NONCE_SLOT = "{{nonce}}"
ASSETS_PATH = "/assets"
NOT_FOUND = 404
CONTENT_HASHED = re.compile(r"-[A-Z0-9]{8}\.\w+$")
"""esbuild's `[name]-[hash]` chunk names: their content never changes under the same name."""
IMMUTABLE = "max-age=31536000, immutable"
REVALIDATE = "no-cache"


def front_end_routes(static_directory: Path, csrf: str) -> list[BaseRoute]:
    template = PAGE_TEMPLATE.read_text(encoding="utf-8")
    assets = frozenset(manifest_digests(static_directory) or ())

    async def page(_request: Request) -> Response:
        nonce = new_nonce()
        headers = {"content-security-policy": content_security_policy(nonce)}
        html = template.replace(CSRF_SLOT, csrf).replace(NONCE_SLOT, nonce)
        return HTMLResponse(html, headers={**headers, "cache-control": NO_STORE})

    async def asset(request: Request) -> Response:
        path: str = request.path_params["path"]
        if path not in assets:
            raise HTTPException(NOT_FOUND)
        return FileResponse(static_directory / path, headers={"cache-control": _caching(path)})

    return [
        Route(PAGE_PATH, page, methods=["GET"]),
        Route(f"{ASSETS_PATH}/{{path:path}}", asset, methods=["GET"]),
    ]


def _caching(path: str) -> str:
    return IMMUTABLE if CONTENT_HASHED.search(path) else REVALIDATE
