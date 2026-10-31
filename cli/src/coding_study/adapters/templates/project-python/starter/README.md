# {{title}}

TODO: one paragraph on what this project builds over its levels.

## Contract

- `app/main.py` defines the class `{{class_name}}`. Keep the module and the class where they are: `cstudy submit` imports `{{class_name}}` from `app.main`.
- `{{class_name}}()` takes no arguments.
- Each level names the methods it adds, with their parameters and return types. Keep those names and signatures.

Everything else is yours: add modules under `app/`, and your own tests under `tests/`.

## Running the tests

From this folder:

```sh
.venv/bin/pytest
```

`uv run --no-sync pytest` works too. From the workspace, `cstudy test {{slug}}` runs the same tests.

Avoid `python -m pytest` here: it puts this folder first on `sys.path`, where a module named like a standard-library one would shadow it. Keep `pyproject.toml` to tool settings: a `[project]` table or a `requires-python` line would make `uv run` manage `.venv`, which is the workspace's shared environment.

## Grading

Your tests are feedback only. `cstudy submit {{slug}}` grades every case of the open levels, hidden ones included, and opens the next level when they all pass.
