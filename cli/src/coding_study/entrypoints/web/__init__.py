"""The local web UI that `cstudy serve` serves: a second driving adapter beside the terminal
(docs/specs/web-ui.md, docs/architecture.md#web-adapter).

Its modules load Starlette, uvicorn and wsproto, so only `cstudy serve` imports them. This one
imports nothing heavy, so the command can check the installed assets before loading the web
stack.
"""

from pathlib import Path

STATIC_DIRECTORY = Path(__file__).parent / "static"
"""The built front end, `manifest.json` and `THIRD_PARTY_LICENSES.txt`
(docs/specs/installation-and-workspaces.md#web-ui-assets)."""
