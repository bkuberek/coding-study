# Inbox

A Python project for the runner conformance suite on the virtual clock: `inbox/inbox.py` defines the entry class `Inbox`, whose waiting methods are `async def`.

`cstudy` imports `Inbox` from `inbox.inbox` and grades each case on an event loop of its own whose clock is virtual. Run the tests with `.venv/bin/pytest`; `pyproject.toml` loads the plugin `cs_support.virtual_clock`, which runs `async def` tests on the same clock.
