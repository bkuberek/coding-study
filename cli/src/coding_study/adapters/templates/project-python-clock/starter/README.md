# {{title}}

TODO: one paragraph on what this project builds over its levels.

## Contract

- `app/main.py` defines the class `{{class_name}}`. Keep the module and the class where they are: `cstudy submit` imports `{{class_name}}` from `app.main`.
- `{{class_name}}()` takes no arguments.
- Each level names the methods it adds, with their parameters and return types; a method that waits is an `async def`. Keep those names and signatures.

Everything else is yours: add modules under `app/`, and your own tests under `tests/`.

## Running the tests

From this folder:

```sh
.venv/bin/pytest
```

`uv run --no-sync pytest` works too. From the workspace, `cstudy test {{slug}}` runs the same tests.

Avoid `python -m pytest` here: it puts this folder first on `sys.path`, where a module named like a standard-library one would shadow it. Keep `pyproject.toml` to tool settings: a `[project]` table or a `requires-python` line would make `uv run` manage `.venv`, which is the workspace's shared environment. Keep `-p cs_support.virtual_clock` in its `addopts`: it loads the plugin that runs `async def` tests on the virtual clock.

## Testing on the virtual clock

`cstudy` grades and tests this project on a virtual clock: an asyncio event loop whose clock moves only while every task waits, so a wait of any length takes no real time. The plugin `cs_support.virtual_clock` runs every `async def` test on that loop, as `cstudy submit` runs each case. The generated tests in `tests/` use its helpers; write yours the same way:

```python
import asyncio

from cs_support.virtual_clock import advance, now, settle

from app.main import {{class_name}}


async def test_a_wait_ends_when_a_value_arrives() -> None:
    store = {{class_name}}()
    waiter = asyncio.create_task(store.wait_for("a", 5000))
    await settle()                 # every task waits
    await advance(1000)            # the clock moves one second forward
    store.put("a", "x")
    assert await waiter == "x"
    assert now() == 1000           # the virtual milliseconds since the test started
```

Read time only through the loop: `asyncio.sleep`, `asyncio.timeout`, `asyncio.wait_for` and `asyncio.get_running_loop().time()` move with the virtual clock, while `time.time()` and `time.monotonic()` stay real. A task that waits on an event, a queue, a timer or another task lets time move; code that blocks the loop's thread (`time.sleep`, a `threading.Lock` its holder keeps, a busy loop) does not, so the case hangs. Tasks still waiting when a test ends are cancelled. A wait that nothing can end, while no timer is due, is a deadlock: the test fails with `DeadlockError` at once, and `cstudy submit` reports the case as `STALLED` with the operation and the virtual time.

Events due at the same instant happen in no fixed order, so the expected values never depend on it.

## Grading

Your tests are feedback only. `cstudy submit {{slug}}` grades every case of the open levels, hidden ones included, and opens the next level when they all pass.
