# Bank Project

A small Python project that grows over four levels. Each level adds methods to `Bank` and builds on the code you wrote for the levels before it, so how you split the code into modules is up to you and part of the exercise.

## Contract

- `bank/bank.py` defines the class `Bank`. Keep the module and the class where they are: `cstudy submit` imports `Bank` from `bank.bank`.
- `Bank()` takes no arguments.
- Each level names the methods it adds, with their parameters and return types. Keep those names and signatures.

Everything else is yours: grow or replace `bank/models.py`, add modules under `bank/`, and add your own tests under `tests/`.

## Layout

| Path | Holds |
|------|-------|
| `bank/bank.py` | `Bank`, with level 1's methods to implement |
| `bank/models.py` | `Account`, a first model type |
| `tests/conftest.py` | A `bank` fixture for your own tests |
| `tests/test_level_<n>.py` | The examples of each open level, written by `cstudy` when the level opens; yours to edit, never rewritten |
| `pyproject.toml` | pytest, pyright and ruff settings |
| `.venv` | A link to the workspace's Python environment, created by `cstudy start`; nothing is installed here |

## Running the tests

From this folder:

```sh
.venv/bin/pytest
.venv/bin/pytest tests/test_level_1.py
```

`uv run --no-sync pytest` works too. From the workspace, `cstudy test bank-project-python` runs the same tests.

Avoid `python -m pytest` here: it puts this folder first on `sys.path`, where a module named like a standard-library one (`random.py`, `types.py`) would shadow it.

Keep `pyproject.toml` to tool settings. A `[project]` table or a `requires-python` line would make `uv run` manage `.venv`, which is the workspace's shared environment.

## Grading

Your tests are feedback only. `cstudy submit bank-project-python` grades every case of the open levels, hidden ones included, against `Bank`, and opens the next level when they all pass. Editing a test file never changes a grade.
