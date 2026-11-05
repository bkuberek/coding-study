# Spec: Service projects (planned)

**Status: planned. Nothing in this spec is built, and implementation has not started.** A service project is a [project problem](problem-format.md#project-problems) where you build a small running service: `cstudy` starts your app locally, with mock servers for third-party APIs and, where the problem declares them, backing services in Docker, and judges it by what it answers over HTTP. Decision record: [ADR 0019](../decisions/0019-service-projects.md), which tags each decision by who made it. Items marked R*n* there are recommendations confirmed when their phase starts. Existing problems, the bank projects included, do not change.

## Names

A service project is `kind: project` with `project.grading: http`. The name is new in the repository; `cache-service` and `notification-service` are catalog slugs and do not collide.

| Term | Meaning | Note |
|------|---------|------|
| Mock server | The Python server cstudy runs for a third-party API | Always "mock server": [`cstudy mock`](cli.md#cstudy-mock) and attempt mode `mock` are the timed practice session |
| Instance | One set of mock servers and, when declared, one stack, owned by one command | `dev` or `graded` |
| Stack | One Docker Compose project that cstudy started | |
| Runtime file | A file cstudy writes into your folder that is visible read-only and outside `code_hash`, the manifest and archives | Not a [generated test file](problem-format.md#generated-test-files), which is tracked and editable |

## Lifecycle commands

Names are fixed, contents are free, and cstudy calls only the standard names. A problem's designer puts whatever the problem needs inside them. Each command is an argument list, never a shell string, run with no shell; anything longer points at a script.

| Command | What it does | Required |
|---------|--------------|----------|
| `install` | Installs the project's dependencies | When the problem declares `requires.lock` |
| `bootstrap` | Brings data to a known state: migrations and seed. Safe to run repeatedly | When the problem declares `services`; otherwise optional |
| `run` | Starts your app in the foreground | Always |
| `test` | Runs the visible tests | Always |
| `reset` | Resets data between hidden cases | Optional |
| `grade_setup` | Problem-owned: applies only the baseline and loads hidden data, before `bootstrap` | Optional |

`install` is not called `init` because [`cstudy init`](installation-and-workspaces.md#cstudy-init) creates a workspace.

### Contract

| Command | When cstudy calls it | Working directory | Added environment | Time limit | Network | Failure |
|---------|----------------------|-------------------|-------------------|------------|---------|---------|
| `install` | `cstudy start`, and any command that needs the project when the lock digest differs from the [install record](#install-rules) | The project root | None | 600 s | Yes | [Install failed](#failure-reporting), exit 4 |
| `bootstrap` | After services are up: at the start of `cstudy dev`, `cstudy test` and `cstudy submit`, and after `grade_setup` in a graded run | The project root | [Instance environment](#environment) | 120 s | No | [Migration failed](#failure-reporting) |
| `run` | After `bootstrap`, in every run that needs the app; by `cstudy dev` only with `--run` | The project root | Instance environment, plus `port_env` | `ready_timeout_s` until the health path answers, then none until cstudy stops it | No | [App did not start](#failure-reporting) |
| `test` | `cstudy test`, with the app running | The project root | Instance environment, plus the visible-only control variables | 120 s | No | Its exit code is a test failure; it never grades |
| `reset` | Once with `CSTUDY_RESET_PHASE=prepare` after `bootstrap`, then with `CSTUDY_RESET_PHASE=apply` before each case with `fresh: true`, with the app stopped | The project root | Instance environment | 30 s | No | Case `error`, and the remaining cases `not_run` |
| `grade_setup` | Graded runs and `cstudy verify` only: after services are up and before `bootstrap` | The project root | Instance environment, plus `CSTUDY_PROBLEM_DIR` and `CSTUDY_GRADED_LEVEL` | 120 s | No | A content error, exit 4, whose output is never shown as a hidden case |

`project.timeouts_s` overrides a limit per command. "No network" is a rule for authors: cstudy has no sandbox ([PRD](../prd.md)) and cannot enforce it, so the [authoring checklist](#ready-rules) includes a run with the network off.

### Environment

| Variable | Set by | Value |
|----------|--------|-------|
| The `env` of each mock server | cstudy | `http://127.0.0.1:<port>` |
| The `x-cstudy.env` of each service | cstudy | The service's URL, with its published port |
| `port_env` (`PORT`) | cstudy, for `run` and `test` | The app's port |
| `CSTUDY_DATA_DIR` | cstudy | An empty private directory: `.cs/runs/<run>/data` in a graded run, `.cs/projects/<slug>.data/` in `dev`. A SQLite problem keeps its file here, which needs no Docker |
| `CSTUDY_MOCK_CONTROL_URL`, `CSTUDY_MOCK_CONTROL_TOKEN` | cstudy, for `test` only | The control interface of a test instance, which holds only visible scenarios. Never set for `run`, and never for a graded instance |

### Three boundaries

1. **The core owns the infrastructure.** Starting and stopping mock servers and stacks, dynamic ports, the runtime `.env`, labels and cleanup are cstudy's. A command must not start a service, or leftovers and port handling fall apart. Commands run after services are up.
2. **Trust follows location.** `commands` live in the problem's manifest, so you cannot change which commands run. A script in the starter that a command points to can be edited by you. That is acceptable for `install`, `bootstrap`, `run` and `test`, because the grader judges behavior over HTTP: rewriting `bootstrap` only changes the app being judged. It is not acceptable for `grade_setup`, whose script and data must live outside the starter, reached through `{problem}`, the only placeholder an argument list may use, and only in `grade_setup`. S19 refuses `{problem}` anywhere else and refuses a `grade_setup` that points into the project root.
3. **Existing problems are unchanged.** Every other problem keeps its per-language runner, generated tests and grading.

### How you reach them

| You run | On a service project |
|---------|----------------------|
| `cstudy start <slug>` | Copies the starter, runs `install`, and starts nothing else. It prints `cstudy dev` as the next step |
| `cstudy test` | Starts a test instance, runs `bootstrap` and `run`, runs `commands.test`, then the visible HTTP cases of the unlocked levels as feedback. Nothing is stored and nothing opens |
| `cstudy submit` | The [graded run](#graded-run) |
| `cstudy dev <slug>` (new) | The dev instance, in the foreground, until Ctrl-C |
| `cstudy verify` | Exercises the commands on the reference ([checks](#checks)) |

`cstudy dev` is the only new verb. `install`, `bootstrap`, `run` and `reset` have no verbs of their own. `cstudy test --debug`, `--case` and `--level` exit 3 on a service project: debug through your own IDE against `cstudy dev`.

```text
cstudy dev [<slug|file>] [--scenario <mock>=<scenario>]... [--run] [--reset-data]
```

| Flag | Effect |
|------|--------|
| `--scenario` | Sets a mock server's visible scenario at start. A hidden or unknown name exits 3 with the visible names |
| `--run` | Also runs `commands.run`, owned by this command |
| `--reset-data` | Removes the dev volume and `.cs/projects/<slug>.data/` before starting |

It prints each URL, the path of `.env`, and one line per request a mock server receives. One dev instance runs per project: a second `cstudy dev` exits 3 and names the holder's process id. The lock is `.cs/projects/<slug>.dev.lock`.

## Manifest sketch

Planned, under `project` in `meta.yaml`. The real schema, `schemas/meta.schema.json`, allows `entry`, `tests` and `clock` today with `additionalProperties: false` and requires `entry`; it also requires `signature` for every problem. Those change at implementation.

```yaml
kind: project
languages: [typescript]
levels:
  - {level: 1, title: Daily desk passes}
comparator: {type: exact}
project:
  grading: http                 # selects HTTP grading; absent means the entry-class grading of today
  commands:
    install: [pnpm, install, --frozen-lockfile, --ignore-scripts]
    bootstrap: [node, scripts/migrate.ts]
    run: [node, src/server.ts]
    test: [node, --test]
    reset: [node, scripts/reset-data.ts]
    grade_setup: [node, "{problem}/grading/grade_setup.ts"]
  app: {port_env: PORT, health: /health, ready_timeout_s: 30}
  mocks:                        # at most 4
    - {name: rooms, env: ROOMS_API_URL, config: mocks/rooms.yaml}
  services: services/compose.yaml
  requires:
    lock: pnpm-lock.yaml
    services: [postgres]
    tools: []                   # see Authoring guidance: a tool outside the language's toolchain
    sizes: {install_mb: 40, images_mb: {db: 160}, memory_mb: 700}
```

| Field | Rule |
|-------|------|
| `grading` | `http`. It excludes `entry`, `tests`, `clock`, `signature`, generated test files and a `concurrency` block |
| `commands` | The [lifecycle commands](#lifecycle-commands). No other key |
| `app.port_env` | The variable your app reads for its port. Your app must read it from the environment and listen on `127.0.0.1` |
| `app.health` | A path that answers 2xx when the app is ready |
| `mocks` | At most 4, each with a unique `name` (lowercase letters, digits, `-`) and a unique uppercase `env` that is not `port_env`. Every path is relative to the problem's directory, not the starter |
| `services` | A compose file, relative to the problem's directory ([Backing services](#backing-services)) |
| `requires` | [What a problem depends on](#what-a-problem-depends-on) |
| `comparator` | The default for cases: `exact`, `unordered`, `unordered-nested` or `float`, applied to the response body |

## Where the files live

Everything grading trusts lives in the problem's own files, not the starter, so you cannot edit it.

```text
problems/<id>-coworking-availability-typescript/
  meta.yaml
  problem.md
  tests.json
  mocks/
    rooms.yaml              # routes and every scenario, visible and hidden
    rooms.API.md            # the vendor's visible documentation
    bodies/availability.json
  services/compose.yaml     # a data-driven problem only
  grading/                  # a data-driven problem only: grade_setup and hidden data
  starter/
    README.md, package.json, pnpm-lock.yaml, tsconfig.json, .gitignore
    src/server.ts
    tests/                  # visible tests, and the helper for the control interface
    vendors/rooms/API.md    # a copy of mocks/rooms.API.md
  solutions/
    explanation.md
    reference/
```

**Vendor documentation.** The starter holds an `API.md` per mock server, a byte-for-byte copy of the problem's file (S20): base-URL variable, routes, response shapes and a table of visible scenario names. It is a copy for reading, so nothing depends on it and `cstudy start --restore` writes it back. Hidden scenarios appear in neither. A failing hidden case in a practice attempt names its scenario, as a failing hidden case already shows its input ([cstudy submit](cli.md#cstudy-submit)); a mock attempt shows only the count.

## Mock server

One Python program serves every problem and language. For an instance, `cstudy` parses and validates the YAML, then starts one process, in its own process group with an [orphan guard](runners.md#process-lifecycle), that listens on one port per mock server and one control port. The process uses the standard library only, as `adapters/process_liveness.py` does, because it receives the configuration as JSON on standard input together with the control token, and answers one JSON line with its ports. A port of 0 means no port race; a dev instance first tries the last port used for each mock server, recorded in `.cs/projects/<slug>.ports.json`.

**Local only.** Every listener binds `127.0.0.1`, and only the port varies. Nothing binds `0.0.0.0`.

### Config format

A planned `schemas/mock.schema.json` validates this format.

```yaml
routes:
  - id: availability
    method: GET
    path: /v1/rooms/availability
    query: {date: "2027-03-01"}      # listed keys must match; others are ignored
    response:
      status: 200
      headers: {Content-Type: application/json}
      body_file: bodies/availability.json
  - id: availability-empty
    method: GET
    path: /v1/rooms/availability
    response:
      status: 200
      body: {rooms: []}              # a mapping or list is sent as JSON; a string as it is
scenarios:
  outage:
    visible: true
    status: 503
  slow:
    visible: true
    delay_ms: 2000                   # the route's own response, late
  malformed:
    route: availability              # one route; without it, every route
    status: 200
    headers: {Content-Type: application/json}
    body: '{"rooms": ['
  rate_limited:
    visible: true
    status: 429
    headers: {Retry-After: "2"}
  rate_limited_then_ok:
    sequence:
      - {status: 429, headers: {Retry-After: "1"}}
      - {status: 200, body_file: bodies/availability.json}
```

| Rule | Detail |
|------|--------|
| Matching | Method and path exact; first match wins. No path templates and no state beyond sequence counters |
| Unmatched | A clear 404 that names the mock server: `{"error": "no route", "mock": "rooms", "method": "GET", "path": "/v1/other"}`, and a log entry with `matched: false` |
| Scenarios | The default is no scenario. A scenario overrides the matched response; a field it leaves out comes from the route. It never applies to an unmatched request |
| Visibility | A scenario is hidden unless `visible: true`, so a forgotten flag cannot leak one. A dev or test instance loads only visible ones |
| `sequence` | One entry per request, in order; the last entry repeats. A counter per scenario |
| Reset | Sequence counters and the log reset between cases |
| Determinism | Bodies are fixed, with no randomness and no clock |
| Delays | Hidden cases keep `Retry-After` and `delay_ms` at 1 to 3 s, so they stay under the 10 s [hang guard](runners.md#hang-guard-and-restarts); a case that needs more sets `hang_guard_ms`. `Retry-After` is given in whole seconds |

### Control interface

A token-protected local interface that the grader uses. It listens on a port of its own, so it is not part of the mocked API, and scenario choice is no query parameter that could leak into the vendor's contract.

| Request | Effect |
|---------|--------|
| `POST /reset` | Clears the log and counters, and sets every mock server to no scenario |
| `PUT /mocks/<name>/scenario` with `{"scenario": "outage"}` | Sets a scenario, or `null` for none; unknown is 404 |
| `GET /mocks/<name>/log` | The request log |

Every request needs `Authorization: Bearer <token>` and a `Host` of `127.0.0.1:<port>`. No response carries CORS headers. The token is random per instance and reaches the child on standard input. The token of a graded instance is never passed to your app, its `test` or any command.

**This is a correctness aid, not a security boundary.** cstudy has a hang guard but no sandbox ([PRD](../prd.md)), and your code runs as you, so it could read a process's memory or the problem's files. The token keeps an honest app from changing a scenario by accident and keeps a stray request out. It does not stop someone determined to cheat themselves.

### Request log

Each entry records what the app sent and what it got.

```json
{"seq": 2, "mock": "rooms", "matched": true, "route": "availability",
 "scenario": "rate_limited_then_ok", "method": "GET", "path": "/v1/rooms/availability",
 "query": {"date": "2027-03-01"}, "headers": {"accept": "application/json"}, "body": null,
 "status": 200, "received_ms": 1042, "responded_ms": 1043}
```

Times are monotonic milliseconds since the last reset. Header names are lowercase. Bodies keep 64 KiB, with `truncated: true` beyond that, and the log keeps 1,000 entries per reset.

## Runtime files

**`.env`** is written, not shipped, because a fixed file cannot hold a port that changes. A dev instance writes `projects/<slug>/.env`, atomically and only when its content differs, with the app's port, every mock server URL and every service URL, under a comment that names `.env.local`. A graded or test instance never writes it, so a running dev app keeps working.

| Rule | `.env` | `.env.local` |
|------|--------|--------------|
| Who writes it | cstudy | You; cstudy never touches it |
| File tree | Visible, read-only | Visible, editable |
| `code_hash`, `cstudy test --watch`, manifest | Out | Out |
| Archive | Out | Out, because archives are tracked and it may hold secrets; `--fresh` carries it to the new folder |
| Workspace `.gitignore` | `projects/*/.env` | `projects/*/.env.local` |
| In a starter | S15 refuses it | S15 refuses it |

This category is new. Today `is_untracked` in `domain/workspace_projects.py` both hides and refuses a path, so it cannot express visible and read-only.

**Precedence.** For `test` and `submit`, cstudy injects the variables into the process environment, and those win over both files. Loaders in starters must keep that: `node --env-file` and `python-dotenv` leave an existing variable alone by default, to be confirmed in the P1 templates. A user loader that forces an override reaches the wrong URL, and the case fails on the request log.

Dev and graded instances are separate, with their own ports and data, so they cannot collide.

## Backing services

Docker is how service projects get backing services such as Postgres, Redis and LocalStack. It is required only by problems that declare `project.services`. A problem with no services, mock-only ones and the existing bank problems included, never needs Docker, and a problem may keep SQLite in `CSTUDY_DATA_DIR` with no Docker at all. This whole section is verified by the P7 spike before anything is built, and if the spike fails, the owner is told first.

### Declaration

The compose file belongs to the problem, so you cannot edit what grading trusts, and it is tool-neutral, so any image can be used.

```yaml
services:
  db:
    image: postgres:17@sha256:<digest of the chosen release>
    environment: {POSTGRES_USER: app, POSTGRES_PASSWORD: app, POSTGRES_DB: app}
    ports: ["127.0.0.1::5432"]
    mem_limit: 512m
    healthcheck:
      test: [CMD-SHELL, pg_isready -U app]
      interval: 1s
      retries: 30
    x-cstudy:
      env: DATABASE_URL
      port: 5432
      url: postgres://app:app@127.0.0.1:{port}/app
```

User code reads `DATABASE_URL`, `REDIS_URL`, `AWS_ENDPOINT_URL` or whatever the problem names, from `.env` in development and from the environment in a run.

### Lifecycle

```text
docker compose -p cstudy-g-<run id> -f <problem>/services/compose.yaml -f .cs/runs/<run>/labels.yaml up --wait
docker compose -p cstudy-g-<run id> port db 5432
docker compose -p cstudy-g-<run id> down -v
```

| Item | Rule |
|------|------|
| App | Stays on the host at first, so the editor, debugger and native tooling keep working, and reaches services through loopback ports. Mock servers stay native Python on the host |
| Ports | Published on loopback with an ephemeral host port, and read back |
| Dev | Project name `cstudy-d-<slug>-<workspace digest>`, a persistent named volume, `down` without `-v` at the end |
| Graded and test | A fresh project name per run, no reused volume, `down -v` at the end |
| A time limit | `up --wait` within 120 s, else [Service failed](#failure-reporting) |
| Your own Dockerfile | A starter may ship one for you to run, ungraded. Inside a container `localhost` is not the host, so such a container needs its own URL for the vendor, and a mock server on `127.0.0.1` may not be reachable from it on Linux. This is unverified and must be resolved before any starter ships Docker files. Running your app in a container is a later option that must solve this, possibly by running the mock server in the compose network |

### Leftovers

Containers outlive a crashed `cstudy`, so the orphan guard and group-kill precedents do **not** cover them. This is a requirement, given earlier memory exhaustion on the owner's machine.

| Rule | Detail |
|------|--------|
| Labels | Everything cstudy starts carries `cstudy.kind` (`dev` or `graded`), `cstudy.workspace`, `cstudy.slug` and `cstudy.owner_pid`, through the generated override file `labels.yaml`. Whether an override labels networks and volumes as well as containers is a spike question |
| Sweep | The next `cstudy start`, `test`, `submit`, `dev` or `serve` of the workspace removes `graded` stacks whose owner is gone (`is_alive` in `process_liveness.py`), stops `dev` stacks whose owner is gone and keeps their volumes |
| Doctor | A `docker leftovers` row `WARN`s with a count and `fix: cstudy doctor --fix`, which removes by label only, never another container or volume |
| Restart | S21 refuses a `restart` policy, so a reboot brings nothing back |
| A gap | Between a crash and the next command, leftovers keep their memory. The spike decides whether the guard also runs `down` |

### Docker states

When a problem needs Docker, cstudy tells these states apart. If Docker is installed but not running, cstudy starts it. If it is not installed, cstudy asks you to install it and gives instructions. cstudy does not install Docker itself. The details are R22 in the ADR, confirmed at implementation.

| State | How it is seen | What happens |
|-------|----------------|--------------|
| Not installed | No `docker` on `PATH` | The [install message](#install-instructions) |
| Installed, no permission (Linux) | The engine refuses the socket | A message of its own that names the group or the command to run |
| Installed, stopped | `docker` exists, the engine does not answer | Started, where cstudy may start it |
| Running, no compose v2 | `docker compose version` fails | The install message |
| Running | Both answer | Nothing to do |

**When cstudy starts the engine.** Only at the moment it is needed: when you start or run a problem that declares services (`cstudy start`, `test`, `submit`, `dev`, and the Web UI's equivalents), and from `cstudy doctor --fix`. Never from `cstudy list`, `cstudy show`, the Problems or Problem view, or plain `cstudy doctor`, because starting Docker's VM costs real memory on your machine. It prints `starting Docker ...` as an `output` event, shows progress, waits up to 120 s for the engine, then reports clearly if it did not come up.

| Platform | Mechanism (to verify at implementation) |
|----------|------------------------------------------|
| macOS | `open -a Docker`, or Docker Desktop's `docker desktop start` where available |
| Linux, Docker Desktop | `systemctl --user start docker-desktop` |
| Linux, system engine | Needs root. cstudy never runs `sudo` for you: it prints the command and exits 4 |

cstudy never stops the engine, since other work may be using it. It only stops its own labeled stacks.

### Install instructions

One short message per platform, with a link to Docker's official install page, shown from the [requirements summary](#what-a-problem-depends-on), `cstudy doctor` and the Web UI's Start. The wording lives in one place, so all three match.

### Doctor

| Row | Status |
|-----|--------|
| `docker` | `ok` with versions when running; `WARN` with the reason and the fix in any other state, never `FAIL`, as the [Go and Rust rows](cli.md#cstudy-doctor) do, since Docker is optional for cstudy overall. `cstudy doctor` exits 0 either way. Any engine that provides a running daemon and compose v2 works; Docker Desktop is verified at minimum, and no other is claimed until tested |
| `docker leftovers` | [Above](#leftovers) |

Plain `cstudy doctor` only asks; it starts nothing. A stopped engine shows `WARN  docker installed, not running    fix: cstudy doctor --fix`.

### Images

Pulled at problem start with visible progress, the same as dependency installs, and they run with no internet afterwards, which fits [NFR-6](../prd.md). The problem records image sizes in `requires.sizes`, and the download size shows before pulling. S21 refuses an image without a digest.

### Resources and CI

One stack per attempt, stopped when the run or the attempt page ends, with `mem_limit` declared on every service (S21) and a total limit that the spike sets. A dev stack and a graded stack can overlap for the length of a run. The spike measures `up --wait` time and memory with Postgres, Redis and LocalStack on macOS and Linux. Linux CI runners have Docker and macOS runners may not by default (verify), so this is a separate CI job.

## Databases

The database and the migration tool are both defined per project, as part of problem design, and cstudy requires neither. A problem picks SQLite or Postgres according to what it teaches, and whichever migration tool suits it. The core has no knowledge of any tool: there is no tool-specific field, only `bootstrap`. Seed data arrives through migrations, and your service reads the database live.

### Grading a schema you design

You design your own schema, so hidden cases cannot seed or assert against tables the problem does not know.

| Step | What happens |
|------|--------------|
| Baseline | The problem ships a baseline schema and baseline data as the starter's migrations |
| Your work | Your migrations run on top, from that known state |
| Hidden data | Loaded into the baseline schema **before** your migrations run, so they must carry existing data forward. That tests real data migrations, and the statement must say so |
| Checks | Requests and comparisons stay HTTP black-box, so no table of yours is named |
| From empty | Migrating from empty is checked as well |

Migration tools track what they applied, so hidden data cannot simply be inserted before anything has run. `grade_setup` therefore applies only the problem's baseline migrations, using the problem's own tool, and inserts hidden data; `bootstrap` then applies the remainder, because the tool's tracking table already records the baseline. The specifics stay inside the designer's script, so the core stays tool-neutral. This flow is **to be proven on the first data-driven problem with its chosen tool**. `CSTUDY_GRADED_LEVEL` lets the script load only the data of the graded levels. Hidden rows use identifiers from a range the statement reserves, so your seed rows cannot collide with them. If you edit a baseline migration, the tool's own checksum report is what you see.

### Contract tables

A design point. For live-read checks, where the service must see a change made behind its back, a problem may declare tables as a stable contract that the grader writes to mid-run and that you may not rename:

```yaml
project:
  contract_tables: [member_credits]
```

A case then names a problem-owned script as `write_data`. **A contract table limits your schema freedom**, so the statement names it, and a problem uses one only when neither the API nor a mock server can make the change.

### Reset

Data resets per run. A problem that needs a reset between cases declares `commands.reset`, and a case asks for it with `fresh: true`. cstudy stops the app, runs `reset` with `CSTUDY_RESET_PHASE=apply`, and starts the app again. `CSTUDY_RESET_PHASE=prepare` runs once after `bootstrap`. PostgreSQL's `CREATE DATABASE ... TEMPLATE` is an example of such a command, not a core feature, and its cost is measured when first used. Without `commands.reset`, `fresh: true` only restarts the app.

### Parallel cases

A case type for N requests against limited capacity. It gives language-neutral concurrency grading, which is what SQLite cannot show, since a row lock and a lost update need a database that serves writers at once.

```json
{"id": "h21", "level": 3, "fresh": true, "repeat": 3,
 "note": "20 requests for the last 5 desk passes",
 "parallel": {"count": 20, "request": {"method": "POST", "path": "/bookings",
              "json": {"product": "desk_pass", "date": "2027-03-01", "member": "m{i}"}}},
 "expected_statuses": {"201": 5, "409": 15},
 "after": {"request": {"method": "GET", "path": "/availability",
                       "query": {"date": "2027-03-01"}},
           "expected": {"status": 200, "body": [{"product": "desk_pass", "available": 0}]}}}
```

`count` is 2 to 64, as for stress workers. The requests start together behind a barrier, `{i}` is the request's index, and `repeat` runs the whole case again, each time from a reset. The verdict counts statuses, never order. A pass finds no race and proves none, so the summary adds a line as for stress cases ([cli](cli.md#cstudy-submit)). A problem with parallel cases has at least one broken overlay that they catch (D7).

## HTTP grading

Planned. One piece of core code covers every language, with no per-language runner work. No runner job is involved. Existing entry-class problems keep their path.

### Graded run

`cstudy submit`, and D1 and D3 of `cstudy verify`:

1. Check `requires` and the install record; install or pull if needed.
2. Start the graded mock server instance, with every scenario.
3. With `grade_setup`, the from-empty check: bring up the stack if `services` is declared, run `bootstrap` on empty data, then discard the data (`down -v` and an empty `CSTUDY_DATA_DIR`). Without `grade_setup`, the `bootstrap` of the next step is itself this check.
4. Bring up a fresh stack if `services` is declared, run `grade_setup` if declared, run `bootstrap` if declared, run `reset` with `prepare` if declared.
5. Start your app with `commands.run` in a process group of its own, with an orphan guard, in the instance environment. Poll the health path until 2xx or `ready_timeout_s`.
6. For each case of the graded levels, in `tests.json` order: `POST /reset`, restart and reset if `fresh`, set scenarios, send `before` requests, send the request, compare, assert on the log.
7. Stop the app by group kill. Stop the mock servers. `down -v`.

At most one graded app and its instance run per attempt, and `.cs/runs/` holds the run's data. An app that exits during a case, or a case past its limit, restarts as a runner does: the case is `error` or `timeout`, and after 3 restarts the remaining cases are `not_run` ([hang guard](runners.md#hang-guard-and-restarts)). The limit per case uses the same order: config `hang_guard.ms`, the case's `hang_guard_ms`, `limits.hang_guard_ms`, else 10 s.

### Hidden HTTP case

Language-neutral, in `tests.json`, with `id`, `visible`, `level`, `note` and `hang_guard_ms` as today. An example that asserts the app waited for `Retry-After` and did not hammer the vendor:

```json
{"id": "h14", "level": 3,
 "note": "a 429 from the room vendor: wait for Retry-After, then retry once",
 "mocks": {"rooms": "rate_limited_then_ok"},
 "request": {"method": "GET", "path": "/availability", "query": {"date": "2027-03-01"}},
 "expected": {"status": 200,
              "body": [{"product": "desk_pass", "date": "2027-03-01", "available": 12},
                       {"product": "meeting_room", "room": "oak", "slots": ["09:00", "10:00"]}]},
 "comparator": {"type": "unordered"},
 "log": [{"mock": "rooms", "route": "availability", "count": 2, "min_gap_ms": 950}]}
```

| Field | Rule |
|-------|------|
| `mocks` | The scenario per mock server; a mock server it leaves out has none. A visible case names visible scenarios only (S23) |
| `before` | Requests sent first, each of which must answer 2xx, for a case that needs state. Optional |
| `request` | `method`, `path`, optional `query`, `headers`, and `json` or `body` |
| `expected.status` | Required |
| `expected.body` | Optional. JSON is compared by `comparator`, anything else as exact text |
| `expected.headers` | Optional. Each listed header must match |
| `comparator` | Overrides the problem's. `exact`, `unordered`, `unordered-nested` or `float` ([Comparators](problem-format.md#comparators)). `checker` is not allowed |
| `log` | Assertions per mock server and route: `count`, `min_count`, `max_count`, and `min_gap_ms`, measured from each response's `responded_ms` to the next request's `received_ms`. A value a little below the wait, here 950 for 1 s, tolerates timers |
| `fresh` | Restart the app and run `commands.reset` first |

`project.clock: virtual` is refused with `grading: http`: these cases run on the real clock. The bound on waits and D11 keep them stable.

### What you see

`--json` and `--events` keep version 1 of the [event stream](cli.md#event-stream), with additive changes only, so the CLI and the Web UI render it:

| Event | On a service project |
|-------|----------------------|
| `output` | Progress: install, image pull, Docker start, `bootstrap` |
| `test_start`, `test_result` | `cstudy test`: one result for `commands.test`, with id `commands.test`; its output streams through `output`, since cstudy does not parse a framework |
| `case_start`, `case_result` | `cstudy submit`, and now also `cstudy test` for the visible cases. `input` holds the request, and `reason` the log assertion that failed (`rooms availability: expected 2 requests, saw 5`) |
| `level_result`, `level_unlocked` | As today, with `methods` empty |

A hidden case in a mock attempt writes no event, as today.

## Dependencies

A project problem may have its own dependencies. Either you run the install or cstudy runs it automatically (owner). The recommendation is automatic.

### Install rules

| Rule | Detail |
|------|--------|
| When | At `cstudy start`, with progress. A resumed attempt, `cstudy test`, `cstudy submit` and `cstudy dev` install again when the lock file's digest differs from the record |
| Record | `.cs/projects/<slug>.install.json`, with the lock's SHA-256, written after success |
| Lock | The project's exclusive [lock](installation-and-workspaces.md#project-folders) is held during an install |
| Retry | A failed install keeps the attempt. It prints the retry, `cstudy start <slug>`, and the Web UI offers a Retry button |
| You add a dependency | With your package manager, while you have network. The digest differs, so the next command installs. The lock file is your file, hashed in `code_hash` |

### Templates per language

The per-language table lives in project templates under `cli/src/coding_study/adapters/templates/`, as `project-<language>-service/`. A new language means a new template and one row in `PROJECT_TEMPLATE_LANGUAGES` in `domain/scaffold.py`, with no new core logic. Only TypeScript and Python are settled, for the first problems. The others are settled when reached.

| Language | `install` | `run`, `test` | State |
|----------|-----------|---------------|-------|
| TypeScript | `pnpm install --frozen-lockfile --ignore-scripts`, as ADR 0018 installs `.cs/lsp/` | `node src/server.ts`, `node --test` | Settled |
| Python | `uv sync --frozen`, with a real `.venv`, not the link to the shared venv | `.venv/bin/python -P -m <module>`, `.venv/bin/python -P -m pytest` | Settled |
| Kotlin, Java | To settle at P10 | To settle | Conflict: Gradle runs `--offline` in [project builds](runners.md#jvm-project-builds) |
| Go | To settle at P11 | To settle | Conflict: `GOPROXY=off` and vendored modules ([ADR 0012](../decisions/0012-go-and-rust.md)) |
| Rust | To settle at P12, if reached | To settle | Conflict: vendored crates and `cargo --offline` ([ADR 0012](../decisions/0012-go-and-rust.md)) |

Those conflicts are template decisions for these problems, and the existing project paths keep what they do.

### Lock files and static checks

S15 today rejects dependencies in a starter and rejects lock files ([starter](problem-format.md#starter)). For a service project that flips:

- A lock file is required when `requires.lock` is declared, and the install must use it exactly. Because a command's content is free, the rule is checked by what it does: D11 fails when `install` changes the lock's digest.
- The starter's limit of 50 files and 256 KiB may not fit a lock file, so lock files are excluded from it.
- `is_untracked` names `uv.lock` and `Cargo.lock`, the workspace `.gitignore` ignores `projects/*/uv.lock` and `projects/*/Cargo.lock`, and an archive deletes them. For a service project the lock is tracked, hashed and archived, and the starter's own `.gitignore` re-includes it.
- A Python starter has a `[project]` table and `requires-python`, which S15 refuses today because of the `.venv` link. A service project has no link, so `cstudy start` writes none and `cstudy doctor --fix` restores none.

**Install scripts.** pnpm blocks dependency install scripts by default as of v10. That is unverified here and is verified at implementation, along with the `pnpm` version the workspace needs: [`cstudy doctor`](cli.md#cstudy-doctor) shows 9.15.9 in its example. Prefer dependencies with no native build. A native package needs an explicit allow list per problem, which the template expresses in `package.json`.

### Authoring guidance: migration tools

A migration tool is chosen at authoring time and counts as a project dependency under these rules: it must be pinned and it must run with no network after `install`. This is guidance for any problem that picks it, not a requirement of cstudy.

**Liquibase**, the owner's preference and neither a default nor a requirement. Checked on 2026-11-05 against [Liquibase's 5.0 release notes](https://docs.liquibase.com/community/release-notes/5-0) and [its license announcement](https://www.liquibase.com/blog/liquibase-community-for-the-future-fsl):

| Fact | Consequence for a problem |
|------|---------------------------|
| Community 5.0 and newer need Java 17 or newer | On a Kotlin or Java problem the JVM is already there. On a TypeScript, Python, Go or Rust problem it adds a requirement the language would not otherwise have, so the problem declares it in `requires.tools`, and `cstudy doctor` and the requirements summary say why it is unavailable without Java |
| The distribution no longer bundles drivers or extensions; they are added through `liquibase lpm` or Maven | Whether a SQLite driver is available this way is unverified: confirm at authoring |
| Community 5.0 and newer are under FSL-1.1-ALv2, which Liquibase states is not OSI open source and which converts to Apache 2.0 two years after each release; versions before 5.0 stay Apache 2.0 | Choose the version line to pin with the license in mind, per problem |
| A JVM start adds time and memory to each `bootstrap` | Not measured. Measure at authoring |

Liquibase's contexts or labels are one way to separate seed changesets, and to apply only the baseline in `grade_setup`. Verify this before relying on it.

## What a problem depends on

The CLI and the Web UI list what a problem depends on, so you know before starting. This extends the display of [ADR 0016](../decisions/0016-jdk-range.md) rather than adding a parallel concept: today a [JDK range](cli.md#the-selected-jdk) marks a language with `!` and a footer in `cstudy list`, names a declared range in `cstudy show`, refuses `cstudy start` with exit 4 and a `fix:` line, disables a language in the Web UI's [Start dialog](web-ui.md#problem-view) with the same reason, and appears as `jdk` in `cstudy list --json`.

| Shown | Source |
|-------|--------|
| Language and toolchain version | The problem's language and doctor's minimums; Java and Kotlin use the existing `jdk` range |
| Whether Docker is needed | `project.services` |
| Each service, with image download size | The compose file and `requires.sizes` |
| Mock servers, by name; they need nothing from you | `project.mocks` |
| Package manager and approximate install size | The lock file's name and `requires.sizes` |
| Total download and approximate memory | `requires.sizes` |
| Whether each is met here, with the reason when it is not | The same checks as `cstudy doctor`, at the moment it is displayed |

### Where it comes from

Recommended, to confirm. The list is a small declared `project.requires` block plus what cstudy derives from the compose file and lock file. A static check (S22) fails when the declared list disagrees with those files, so it cannot drift. `cstudy verify` measures sizes and D11 fails when a declared size is more than 25% away. It does not write them, since cstudy never writes to the content root except through `cstudy new`: it prints the measured values for the author to copy.

### Where it shows

| Surface | What |
|---------|------|
| [`cstudy list`](cli.md#cstudy-list) | A `NEEDS` column, only when a listed row has a value: `docker postgres`. Content only: it runs no process, as ADR 0016 rejected a `java -version` per command against NFR-2's 500 ms |
| `cstudy list --needs` | `--needs none` keeps problems that need nothing beyond the language's toolchain; `--needs docker` or a service name keeps those that do |
| `cstudy list --json` | Each entry gains `requires`, next to `jdk`, null for other problems |
| [`cstudy show`](cli.md#cstudy-show) | The full list above the statement, with each requirement's state. It reads state and starts nothing |
| [Problems view](web-ui.md#problems-view) | The marker in the table and a filter of the same values |
| [Problem view](web-ui.md#problem-view) | The full list |

An example, with illustrative figures:

```text
needs
  language   typescript · node 24 or newer         ok    node v24.18.0
  packages   pnpm · about 40 MB installed
  docker     running engine and compose v2         WARN  not installed · <install message>
  services   postgres · 160 MB download
  mocks      rooms (nothing to install)
  total      about 170 MB download, about 700 MB memory
```

### At Start

`cstudy start` and the Web UI's Start show the summary before any download begins. They ask for confirmation only when something will be downloaded or a requirement is missing. `cstudy start --yes` skips the prompt for scripts; without a terminal and without `--yes`, a start that would download exits 3 and names the flag. If a requirement is missing, Start says what to install rather than failing midway, exiting 4 before it writes anything, as a JDK outside the range does. A stopped Docker engine is not missing: Start starts it ([Docker states](#docker-states)).

## Offline behavior

After the install and the image pull, a service project runs with no internet: mock servers, the grader and the app talk over loopback, and `bootstrap`, `run`, `test` and `grade_setup` must not need the network. If the install has not happened and there is no network, cstudy says so rather than showing a raw error:

```text
coworking-availability-typescript needs its dependencies, and the install could not reach the network.
Connect to the network, then run: cstudy start coworking-availability-typescript
```

## Failure reporting

| Failure | Report | Exit, `--json` outcome |
|---------|--------|------------------------|
| Install failed | The command, the tail of its output, and the retry | 4, `error`. Attempt kept |
| Docker missing, stopped and could not start, or no permission | The state's message ([Docker states](#docker-states)) | 4, `error` |
| Service failed: `up --wait` timed out or an image cannot be pulled | The service, its log tail, and the retry | 4, `error` |
| Mock server port bind failed | The mock server and the error | 4, `error` |
| Config error in a mock config, the compose file or the manifest | The file and the reason, as a content error; S19 to S21 catch it first | 4, `error` |
| Migration failed (`bootstrap`) | As an install failure: the command and its output tail, except in a mock attempt, where only that it failed on existing data. In `cstudy submit` it is your code, so the submission is stored, as a [load failure](cli.md#cstudy-submit) is | 2, `load_failed` |
| `grade_setup` failed | That the problem is at fault, without its output | 4, `error` |
| App did not start: it exited | The exit code and the tail of its standard error, at most 4 KiB | 2, `load_failed` |
| Health timeout | The URL, the time limit, the stderr tail, and a reminder to read `port_env` and listen on `127.0.0.1`: on some machines `localhost` binds `::1` only | 2, `load_failed` |
| App died during a case | Case `error`, with the stderr tail; a restart | 1, `failed` |

## Resources

| Resource | Expectation |
|----------|-------------|
| Graded runs | At most one graded app and its instance per attempt |
| Mock server memory | At most 30 MB resident per instance, an expectation P2 measures |
| Disk per project | `node_modules` or `.venv`, which share the pnpm store and uv cache by links where the file system allows it, to be measured at P4 and P5 |
| Docker | [Backing services](#resources-and-ci) |
| Language servers | Each project still counts toward `cstudy serve`'s limit of four language servers |

### Cleanup

There is no `cstudy reset` and no command that removes a problem; verified against `entrypoints/commands/`.

| Action | What it removes |
|--------|-----------------|
| `cstudy start --fresh`, or a review attempt | `archive_folder` runs `remove_untracked` first, so `node_modules`, a real `.venv`, and caches are deleted, not archived. The next start installs again |
| Deleting `projects/<slug>/` by hand | Everything in it. A resumed attempt copies the starter and installs again |
| `.cs/build/projects/<slug>/` | The reference's copy and its install, recreated by `cstudy verify` |
| `cstudy doctor --fix` | Docker leftovers, by label only |
| `cstudy dev --reset-data` | The dev volume and the dev data directory |
| Images | Never removed by cstudy, since other work may use them |

## Language servers

Planned. A language server must not read a mock config or a hidden case, and it needs no new hidden directory, as long as these rules hold. ADR 0018's four [hidden directories](web-ui.md#hidden-directories) are `.cs/build/`, `.cs/cases/`, `.cs/runs/` and the content root.

| Item | Where it is | Covered by |
|------|-------------|------------|
| Mock configs, compose files, `grading/`, `tests.json` | The problem's files | The content root |
| A graded run's override, data and logs | `.cs/runs/<run>/` | `.cs/runs/` |
| A reference's copy and install | `.cs/build/projects/<slug>/` | `.cs/build/` |
| Copies of hidden files | Not allowed: cstudy reads them from the problem and passes them on standard input or by path | |

Three gaps, none new:

- Your own problems under `<workspace>/problems/` are not hidden today, for a reference or for this. You wrote them, so nothing is exposed that you did not write.
- A content root that holds the workspace, such as a checkout, is left out of the script's list, since the server could not work without it.
- A server that is not a Node program relies on the broker's filtering alone until its ADR 0018 phase adds its own control. That matters for Kotlin, Java, Go and Rust service projects.

Service projects work with code intelligence through existing roots: the session's root is the project folder, basedpyright resolves imports through the folder's `.venv`, and tsserver through its `node_modules`. P4 and P5 check that against the real servers.

## Web UI

| Item | Phase |
|------|-------|
| The page runs a dev instance of mock servers while the attempt page is open, as it runs [language servers](web-ui.md#lifecycle-and-limits), with the same group stop and idle rule | P2 |
| A stack starts only on request, because of its memory, and stops with the page | P8 |
| Mock server status and a scenario picker over the control interface | P6 |
| `.env` as a read-only tree entry, `editable: false`, `origin: "runtime"` | P1 |
| The dependency list, and Start's summary and confirmation | P6, P8 |
| The Docker messages in Start and the [Health view](web-ui.md#health-view) | P8 |

If a terminal holds the dev instance, the page shows that and does not start a second.

## Checks

### Static

| Check | Rule |
|-------|------|
| S14, S15, S16 (changed) | With `grading: http`: no `entry`, `tests`, `clock`, `signature` or generated-test rules. The starter holds `README.md`, its lock file, and no `.env` or `.env.local`. S15's rules on `package.json`, `pyproject.toml` and lock files [flip](#lock-files-and-static-checks) |
| S19 (new) | `commands` holds only the standard names; `run` and `test` are declared, `install` with `requires.lock`, `bootstrap` with `services`; each is a non-empty list of strings; `{problem}` only in `grade_setup`, whose script lies outside the starter; `app` complete; at most 4 mock servers with unique names and variables |
| S20 (new) | Every mock config valid against `schemas/mock.schema.json`; `body_file` stays inside `mocks/` and exists; every scenario's `delay_ms` and `Retry-After` are at most 3 s; `rooms.API.md` and its starter copy are byte-identical and list exactly the visible scenarios |
| S21 (new) | The compose file holds images pinned by digest and no `build`; each port is `127.0.0.1::<port>`; `mem_limit` and `healthcheck` on every service; no `restart`, `container_name`, top-level `name`, `network_mode: host`, `privileged`, external volume or bind mount outside the problem; `x-cstudy` complete |
| S22 (new) | `requires` agrees with the compose file, the lock file and `commands`: `services` names the images' repositories, `lock` exists and `images_mb` has a row per service |
| S23 (new) | Every HTTP case: `mocks` names known scenarios, visible ones only in a visible case; `log` names known routes; `fresh` with data needs `commands.reset`; `count` from 2 to 64; waits within the case's hang guard |

### Dynamic

| Check | Rule |
|-------|------|
| D1 (changed) | The starter: `install` and `bootstrap` succeed, `run` answers the health path, a graded run of level 1 reports a result for every case (cases may fail), `test` runs without crashing |
| D3 (changed) | The reference passes every HTTP case through the [graded run](#graded-run), as the starter with its overlay |
| D9 (changed) | The reference: `commands.test` exits 0, and the visible cases pass. No generated test files exist |
| D7 (extended) | A broken overlay passes every sequential case and fails each parallel case in its `caught_by` |
| D11 (new) | `install` leaves the lock's digest unchanged; `bootstrap` succeeds from empty and twice in a row; three runs of the reference give the same verdicts; the slowest case stays within 50% of its hang guard; measured sizes are within 25% of `requires.sizes`. Outside NFR-3's 30 s per problem, as D6, D7 and D10 are |

### Ready rules

The [ready rules](authoring.md#ready-criteria) can be met with these changes:

| Rule today | Change |
|------------|--------|
| At least 2 visible and 2 hand-written hidden cases per level, at least 8 hidden in all | Kept. Four levels already give 8. Visible cases feed the statement's examples and `cstudy test` |
| Exactly one approach, `optimal`, with its overlay and `### Design` | Kept |
| A starter with `README.md` | Kept, and it also names how to run the app and which variables it reads |
| D9 passes | Its meaning changes, as above |
| S5: examples per level, generated `Methods to add` | Examples render a request and a response. A level names the endpoints to add |
| New | D11 passes. A data-driven problem also has a baseline, its `grade_setup` runs, and a from-empty `bootstrap` passes. A problem with parallel cases has a broken overlay caught. The author runs it once with the network off, since cstudy cannot check that |

## The first problem

Original to cstudy ([ADR 0004](../decisions/0004-original-problem-wording.md)). A coworking space sells desk passes, counted per day, and meeting rooms, booked in time slots from a room vendor. One API serves both. Slugs: `coworking-availability-typescript`, then `coworking-availability-python`, each a separate problem as [ADR 0014](../decisions/0014-project-problems.md) requires.

| Level | What it asks |
|-------|--------------|
| 1 | The existing daily-count endpoint works, and you get oriented in the codebase. One small change as well, such as refusing a date out of range with a 400, so the starter does not pass untouched and `cstudy done` keeps its meaning |
| 2 | Integrate the room vendor and serve both product kinds from one endpoint |
| 3 | Vendor failure handling: outage (503), slow, malformed and rate limited (429) |
| 4 | A second vendor with a different response shape, on a second mock server |

The stack per language is chosen at authoring time, with Express or an equivalent now allowed. A level's cases check a response that degrades as the statement says when the vendor fails, for example desk passes served and rooms marked unavailable. A slow-vendor case needs no upper time bound on a loaded machine: an app with no timeout returns the full answer late, and the body differs.

**What cannot be auto-graded.** Open-ended design discussion, such as caching vendor data and for how long, a circuit breaker, adding a third vendor, or how the API would change under load, goes in `solutions/explanation.md`, under `### Design`.

**Data-driven problems** come after the Docker services phase, in the same theme, with the domain, database and migration tool chosen at authoring: for example, splitting a member's plan into its own table, carrying existing members forward, and refusing bookings beyond capacity under parallel requests.
