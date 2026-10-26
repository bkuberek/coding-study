# coding-study workspace

Your practice workspace for [coding-study](https://github.com/bkuberek/coding-study): your solutions, notes, attempt history and your own problems. Version it in its own git repository if you like; `cstudy` never commits for you.

## Daily loop

```bash
cstudy next                      # what to practice
cstudy start two-sum --lang python
cstudy test                      # run your code against the cases
cstudy done --rating ok          # finish the attempt and schedule a review
```

Run `cstudy` anywhere inside this directory, or from elsewhere with `cstudy --workspace <path>` or `CSTUDY_WORKSPACE=<path>`.

## Layout

| Path | What it holds |
|------|---------------|
| `python/`, `typescript/`, `jvm/` | One practice project per runtime; open each as the editor root (IntelliJ: open `jvm/` as a Gradle project) |
| `notes/` | Your answers to system design and code review items |
| `problems/` | Problems you write yourself (`cstudy new <slug>`); they join the catalog |
| `.archive/` | Earlier attempts that `cstudy start --fresh` and reviews moved aside |
| `.cs/workspace.toml` | Marks this directory as a workspace; keep it in version control |
| `.cs/`, `.statements/`, `progress.db` | Caches, the runner runtime, rendered statements and your progress; ignored, per machine |

## On a new machine

After cloning this workspace, install `cstudy` and run `cstudy doctor --fix` here: it recreates the runner runtime in `.cs/runtime/`, the Python venv, `node_modules` and the Gradle build. Progress lives in `progress.db`, which is not committed; `cstudy export` writes `progress-export.json`, which you may commit, and `cstudy import` restores it.
