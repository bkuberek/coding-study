# Safe Redaction

A small Python project that grows over four levels. A model finds the emails, phone numbers and names in a text, and your `Redactor` hides them before the text goes anywhere else. The model is not to be trusted, so most of the work is making `Redactor` safe when it is wrong. Each level adds methods to `Redactor` and builds on the code you wrote for the levels before it, so how you split the code into modules is up to you and part of the exercise.

## Contract

- `redaction/redactor.py` defines the class `Redactor`. Keep the module and the class where they are: `cstudy submit` imports `Redactor` from `redaction.redactor`.
- `Redactor()` takes no arguments.
- Each level names the methods it adds, with their parameters and return types. Keep those names and signatures.
- Offsets count characters (Python's `str` indexes), starting at 0. A span `start:end` includes the character at `start` and not the one at `end`, as a slice does.

Everything else is yours: add modules under `redaction/`, and add your own tests under `tests/`.

## Layout

| Path | Holds |
|------|-------|
| `redaction/redactor.py` | `Redactor`, with level 1's method to implement |
| `redaction/models.py` | `Proposal`, what the extractor proposes: `start`, `end`, `label` and `quote` |
| `redaction/extractor.py` | `propose(text)`, a fixed-rule stand-in for the model, unreliable on purpose. Its docstring lists how. The graded cases give your code proposals as plain lists, so you never call it from `Redactor`; use it in your own tests |
| `tests/conftest.py` | A `redactor` fixture for your own tests |
| `tests/test_extractor.py` | A few tests of what the extractor gets wrong |
| `tests/test_level_<n>.py` | The examples of each open level, written by `cstudy` when the level opens; yours to edit, never rewritten |
| `pyproject.toml` | pytest, pyright and ruff settings |
| `.venv` | A link to the workspace's Python environment, created by `cstudy start`; nothing is installed here |

## Running the tests

From this folder:

```sh
.venv/bin/pytest
.venv/bin/pytest tests/test_level_1.py
```

`uv run --no-sync pytest` works too. From the workspace, `cstudy test safe-redaction-python` runs the same tests.

Avoid `python -m pytest` here: it puts this folder first on `sys.path`, where a module named like a standard-library one (`random.py`, `types.py`) would shadow it.

Keep `pyproject.toml` to tool settings. A `[project]` table or a `requires-python` line would make `uv run` manage `.venv`, which is the workspace's shared environment.

## Grading

Your tests are feedback only. `cstudy submit safe-redaction-python` grades every case of the open levels, hidden ones included, against `Redactor`, and opens the next level when they all pass. Editing a test file never changes a grade. Nothing here calls a real model.
