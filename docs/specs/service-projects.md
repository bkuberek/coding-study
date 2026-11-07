# Spec: Service projects

**Status: built through P7: the sandbox, the lifecycle commands, the mock server, the HTTP grader and `cstudy dev`, so a service project works from `cstudy start` to `cstudy submit`, on macOS with Docker Desktop, and the first catalog problem, [`coworking-availability-typescript`](#the-first-problem), uses them. What is still planned says so where it stands: the Python version (P8), backing services (P10), code intelligence and the Web UI (P9), and parallel and multi-step cases (P10, P11).** A service project is a [project problem](problem-format.md#project-problems) where you build a small running service: `cstudy` runs your app in a Docker sandbox, with mock servers for third-party APIs and, where the problem declares them, backing services, and judges it by what it answers over HTTP. Decision record: [ADR 0019](../decisions/0019-service-projects.md), which tags each decision by who made it. Items marked R*n* there are recommendations confirmed when their phase starts. Phases P*n* are the ADR's. Existing problems, the bank projects included, stay native, need no Docker and do not change.

## Names

A service project is `kind: project` with `project.grading: http`. The name is new in the repository; `cache-service` and `notification-service` are catalog slugs and do not collide.

| Term | Meaning | Note |
|------|---------|------|
| Mock server | The Python server cstudy runs for a third-party API | Always "mock server": [`cstudy mock`](cli.md#cstudy-mock) and attempt mode `mock` are the timed practice session |
| Stack | One Docker Compose project that cstudy started, owned by one command | `dev`, `test` or `graded` |
| App container | A container of the problem's toolchain image, with your project folder mounted | The long-running one for `run`, and one-off ones for the other commands |

## Sandbox

Service projects always run in Docker, as their sandbox (owner, O15). Per-project dependencies mean running third-party code and install scripts, and security catalog starters contain deliberate flaws, so an unfixed SSRF starter could otherwise reach your LAN or a cloud metadata endpoint. Docker gives a boundary at the project folder: nothing above it is visible. The [P1 spike](../decisions/0019-service-projects.md#the-p1-spike) measured this section on macOS with Docker Desktop, and what it could not measure on Linux stays [unproven](#unproven-on-linux).

It runs on your own Docker, which you use for other things. cstudy never changes, requires changing, or recommends changing an engine setting; its limits are per container, on its own stacks only; and it never stops the engine (owner, O16).

### What a stack holds

cstudy generates the compose file, `.cs/runs/<run>/stack.yaml`, and merges the problem's own [backing services](#backing-services) with it.

| Container | Image | Sees | Networks |
|-----------|-------|------|----------|
| `app` | The problem's toolchain image, `project.image` | Your project folder, and the data volume at `/data` | `sandbox` |
| `cstudy-mocks` | A pinned Python image | cstudy's mock server code and the [rendered configs](#mock-server), both read-only | `sandbox`, with each mock server's name as an alias |
| `cstudy-forward` | The same pinned Python image | cstudy's forwarder code, read-only | `sandbox` and `edge` |
| Backing services | The problem's, by digest | Their own volumes | `sandbox` |

### Mounts

| Item | Rule |
|------|------|
| Project folder | Bind-mounted read-write at the **same absolute path** as on your machine, so a path in an error message, a diagnostic or a debugger means the same thing on both sides. It is the working directory |
| What sandboxed code leaves there | The folder shows on your machine as your code left it, so a file `cstudy` reads there can be a link to anything, a named pipe, a device or a huge file. `cstudy` reads `pyproject.toml` and `go.mod` with no link followed, only as a regular file, and only their first MiB, and writes a missing `go.work` through no link |
| Parent folders, `.cs/`, your home | Not visible |
| Toolchain links | The links and relative paths of [existing project folders](installation-and-workspaces.md#project-folders) (`.venv` to the shared venv, `go.work`, `.cargo/config.toml`, the workspace's `node_modules`) do not apply: the image is the toolchain, and dependencies are installed into the folder |
| Links | A bind mount follows a link to wherever it points on your machine, so `cstudy` refuses to start a stack when `.devcontainer` or a problem's `grading` folder is a link |
| Docker socket | Never mounted |
| Data | `CSTUDY_DATA_DIR` is `/data`: a persistent named volume in `dev`, a fresh one per `test` or `graded` stack. A SQLite problem keeps its file here |
| Dependencies | `node_modules` and `.venv` stay in the project folder on the bind mount, so your editor can read them. P1 measured it about as fast as a volume for an install (R30) |
| Install cache | A named volume per project for the pnpm store or uv cache, mounted only in `install` containers, in a compose project of its own, `cstudy-i-<slug>-<workspace digest>`. It outlives each install, and sharing it across projects, which would save about 1 s, is not done, since one install could poison another's cache |

### Networks

| Network | Who | Egress |
|---------|-----|--------|
| `sandbox` (`internal: true`) | Everything in the stack | None: `bootstrap`, `run`, `test`, `reset` and `grade_setup` cannot reach the internet, your LAN or a metadata address. DNS is no way out either, as measured on Engine 29: the engine's name server answers an outside name with `SERVFAIL` in under 0.2 ms, where an ordinary bridge takes about 30 ms to ask upstream, and `host.docker.internal` resolves to nothing and the addresses behind it are unreachable, so D11 probes addresses alone |
| `edge` (an ordinary bridge) | `cstudy-forward` only | Holds no user code |
| An ordinary bridge, `egress` | `install` containers (and `cstudy dev --exec --network`, planned) only, with no mock server or service attached | Yes, and P1 measured that it reaches your LAN and this machine's loopback services too |

**The catch.** A service only on an `internal: true` network publishes nothing, and `docker compose port` prints `:0` and exits 0 (measured), which `cstudy` treats as a failure. So the forwarder above, a small TCP relay, joins both networks. It publishes on `127.0.0.1` with a dynamic host port, read back with `docker compose port`:

| Published | When | Why |
|-----------|------|-----|
| Your app's port | Every stack | The grader, your browser and `curl` |
| The mock control port | Every stack, token-protected | The grader and the Web UI only. It is the one exception to "only the app's port is published". A grader inside the network, the alternative in R24, would remove it |
| A debug port | `cstudy dev --debug` only (planned), never in a graded stack | Your [debugger](#your-own-ide) |

Mock servers and services have stable names and publish nothing. Nothing is ever published beyond `127.0.0.1`. Inside the containers your app listens on all interfaces, because the forwarder is another container.

### Hardening

On every container cstudy generates, the app first (R23):

| Setting | Value |
|---------|-------|
| User | Non-root: your UID and GID, so files in the project folder stay yours. A one-line `/etc/passwd`, read-only, names them. A one-off with `CAP_CHOWN` alone hands a fresh named volume to you |
| Capabilities | `cap_drop: [ALL]` |
| Privileges | `security_opt: [no-new-privileges:true]` |
| Filesystem | `read_only: true`, with tmpfs for `/tmp` and the home directory |
| Setuid bits | Your code can set them on files that show as yours on your machine, so `cstudy` takes them off every regular file in the project folder before and after a stack: no link is followed, a file nobody can read or a folder nobody can enter hides none, and such a folder gets its mode back |
| Limits | `mem_limit` and `pids_limit`, per container: app 512m and 256 pids, a helper 64m and 32, an install 1g and 512. A problem may declare `app.mem_limit` |
| Stopping | `init: true` and a 2 s grace, or each `down` costs 10 s with Node as PID 1 |
| Logs | `json-file` with `max-size: 10m` and `max-file: 3`, per container, so a chatty app cannot fill your disk through the engine's logs: an app that printed 50 MiB kept 24 MiB (measured). `cstudy` changes no engine setting for this |
| Environment | [Explicit only](#environment). Nothing from your machine leaks in, especially real API keys |

A problem-owned service gets `no-new-privileges` and the limits, since an engine such as Postgres needs its own user and writable paths.

### Honest limits

- The project folder stays writable by the code. It holds no secrets, and it is versioned practice work.
- On Linux, access to Docker is effectively root. cstudy cannot reduce it, and the install message says so.
- `install` has the internet, so whatever it runs can send out what it can read, the project folder and nothing above it, and it can reach your LAN and a service bound to `127.0.0.1` on your machine. Install scripts are off, so that is the package manager and nothing a package brings; a package that needs a build fails its install. `cstudy` says this at every install.
- This protects your machine from your code. It does not stop you cheating yourself: you can read the problem's files from your own shell.

### Lifecycle

```text
docker compose -p cstudy-g-<owner pid>-<run id> -f .cs/runs/<stack>/stack.yaml up --wait --wait-timeout <s> --pull never
docker compose -p cstudy-g-<owner pid>-<run id> port cstudy-forward 8000
docker compose -p cstudy-g-<owner pid>-<run id> down -v
```

| Item | Rule |
|------|------|
| Dev | Project name `cstudy-d-<slug>-<workspace digest>`, a persistent named volume, `down` without `-v` at the end |
| Graded and test | A fresh project name per run, no reused volume, `down -v` at the end. The name holds the owner's process id, since a network or a volume carries no owner label. Dev and graded stacks stay separate, so they cannot collide |
| Standard input | Every compose call runs at end of file, and never with `-y`: a label that changes on a volume makes compose ask whether to recreate it, which hangs on a pipe and loses the data under `-y` |
| Current folder | The Docker client and the guard run in a folder of cstudy's own, not the one you ran `cstudy` in: without `-f`, as in every `down`, compose reads `.env` from its current folder, and a `COMPOSE_PARALLEL_LIMIT=abc` there makes it refuse (measured) |
| [Two clocks](#two-clocks) | `up --wait` within the startup budget, 300 s unless `project.timeouts_s.startup` says, else [Service failed](#failure-reporting). It says it is the budget, and that nothing about your code changes |

### Leftovers

Containers outlive a crashed `cstudy`, so the orphan guard and group-kill precedents do **not** cover them. This is a requirement, given earlier memory exhaustion on the owner's machine.

| Rule | Detail |
|------|--------|
| Labels | Everything cstudy starts carries `cstudy.kind` (`dev`, `test`, `graded` or `install`), `cstudy.workspace` and `cstudy.slug`, and its containers `cstudy.owner_pid` too |
| Guard | A process of its own holds a pipe `cstudy` alone writes to, and when the pipe ends, however `cstudy` ended, removes the stack's one-offs, runs `docker compose -p <stack> down`, with `-v` for `test` and `graded`, and removes the run's folder. P1 measured 0.5 s from SIGKILL to nothing left |
| Sweep | For a guard that died too, the next `cstudy start`, `test`, `submit` or `dev` of the workspace removes `graded` and `test` stacks whose owner is gone (`is_alive` in `process_liveness.py`), stops `dev` stacks whose owner is gone and keeps their volumes. It groups containers by compose project, then takes strays by label |
| One-offs | `install`, `commands.reset`, a second `bootstrap` and the egress probe run in `docker compose run` containers. Killing that client, at a limit, on Ctrl-C or with `cstudy`, leaves the container running, and `docker compose down` leaves it and its network and exits 0, with `--remove-orphans` too unless `-f` names the stack's file (measured). So `stop`, the guard and the sweep first remove a stack's one-offs by label, and a one-off past its limit goes at once, before whatever comes next |
| Names | Anyone can write a label, and a container someone else ran can carry `cstudy.kind` and name any compose project. So only a name of cstudy's own form, `cstudy-[dtgi]-...` in lowercase letters, digits, `-` and `_`, counts as a stack, a stray network or a stray volume. Anything else is ignored, before any `down` or removal, and a run's folder is removed only under the runs folder. `docker compose -p <malformed> down -v` exits 0 with nothing done, so the exit code cannot be what protects the folder (measured) |
| Doctor | A `docker leftovers` row `WARN`s with a count and `fix: cstudy doctor --fix`, which removes by label only, never another container or volume |
| Restart | S21 refuses a `restart` policy, so a reboot brings nothing back |

### Docker states

Every service project needs Docker. If Docker is installed but not running, cstudy starts it. If it is not installed, cstudy asks you to install it and gives instructions. cstudy does not install Docker itself. The check is `docker info`, which starts nothing and wakes no idle VM, and never `docker desktop status`, which P1 saw say `stopped` while the engine answered. An idle VM wakes by itself when a stack starts, in about 1.4 s, so `docker info` answering means no start is needed.

| State | How it is seen | What happens |
|-------|----------------|--------------|
| Not installed | No `docker` on `PATH` | The [install message](#install-instructions) |
| Installed, no permission (Linux) | The engine refuses the socket | A message of its own that names the group or the command to run, and that the group is effectively root |
| Installed, stopped | `docker` exists, the engine does not answer | Started, where cstudy may start it |
| Running, no compose v2 | `docker compose version` fails | The install message |
| Running | Both answer | Nothing to do |

**When cstudy starts the engine.** Only at the moment it is needed: when you start or run a service project (`cstudy start`, `test`, `submit`, `dev`, and the Web UI's equivalents), and from `cstudy doctor --fix`. Never from `cstudy list`, `cstudy show`, the Problems or Problem view, or plain `cstudy doctor`, because starting Docker's VM costs real memory on your machine. It prints `starting Docker ...` as an `output` event, shows progress, waits up to 120 s for the engine, then reports clearly if it did not come up.

| Platform | Mechanism (starting from fully quit is not measured) |
|----------|------------------------------------------|
| macOS | Docker Desktop's `docker desktop start --detach`, then `open -a Docker` |
| Linux, Docker Desktop | `systemctl --user start docker-desktop` |
| Linux, system engine | Needs root. cstudy never runs `sudo` for you: it prints the command and exits 4 |

cstudy never stops the engine, since other work may be using it. It only stops its own labeled stacks.

### Install instructions

One short message per platform, with a link to Docker's official install page, shown from the [requirements summary](#what-a-problem-depends-on), `cstudy doctor` and the Web UI's Start. The wording lives in one place, so all three match. Docker Desktop's license requires a paid plan at larger companies: the message says so and links the terms, without figures, which are verified when it is written.

### Doctor

| Row | Status |
|-----|--------|
| `docker` | Engine 25 or newer, since the healthchecks use `start_interval`. `ok` with versions when running; `WARN` with the reason and the fix in any other state, never `FAIL`, as the [Go and Rust rows](cli.md#cstudy-doctor) do, since Docker is optional for cstudy overall. `cstudy doctor` exits 0 either way. Any engine that provides a running daemon and compose v2 works; Docker Desktop is verified at minimum, and no other is claimed until tested |
| `docker leftovers` | [Above](#leftovers) |

Plain `cstudy doctor` only asks, with `docker info` and `docker compose version`; it starts nothing. A stopped engine shows `WARN  docker installed, not running    fix: cstudy doctor --fix`.

### Images

| Image | Pinned where | Note |
|-------|--------------|------|
| Toolchain, per language | `project.image`, from the template | By digest of the multi-architecture index, so macOS on arm64 and Linux on amd64 share one pin. `node:24-slim` with `corepack pnpm`, and the uv image for Python, which holds uv and Python 3.13 |
| Mock server and forwarder | cstudy's own code | One pinned Python image; standard library only, so nothing is built. The code is always copied under `.cs/runs/<stack>/`: Docker Desktop refuses a Homebrew prefix, and silently mounts its own VM's folder for `/usr/local/bin` |
| Backing services | The problem's compose file | S21 refuses an image without a digest |

All are pulled on demand at problem start with visible progress, the same as dependency installs, and they run with no internet afterwards, which fits [NFR-6](../prd.md#non-functional-requirements). The problem records image sizes in `requires.sizes`, and the download size shows in the requirements list before pulling.

### Resources and CI

One stack per run, stopped when the run ends, with `mem_limit` on every container. A dev stack and a graded stack can overlap for the length of a run. P1 measured the stacks at 71 to 667 MiB in use, and most of what Docker costs on your machine is its VM, not the containers. The tests on a real engine run in CI in a job of their own, `sandbox`, on Linux: path-gated to what can affect the sandbox, one job with no matrix and no schedule, within 15 minutes.

## Lifecycle commands

Names are fixed, contents are free, and cstudy calls only the standard names. A problem's designer puts whatever the problem needs inside them. Each command is an argument list, never a shell string, run with no shell inside an app container; anything longer points at a script.

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

Every command runs with the project root as its working directory.

| Command | When cstudy calls it | Where it runs | Added environment | Time limit | Network | Failure |
|---------|----------------------|---------------|-------------------|------------|---------|---------|
| `install` | `cstudy start`, and any command that needs the project when the lock digest differs from the [install record](#install-rules) | A one-off app container | Fixed variables only | 600 s | Internet | [Install failed](#failure-reporting), exit 4 |
| `bootstrap` | After services are up: at the start of `cstudy dev`, `cstudy test` and `cstudy submit`, and after `grade_setup` in a graded run | A one-shot of the stack that `app` depends on, so one failure path and a failed one stops the start | [Environment](#environment) | Within the startup budget | `sandbox` | [Migration failed](#failure-reporting) |
| `run` | As the `app` container's own command, so a crash ends the container and `up --wait` catches it, after `bootstrap`, in every run that needs the app (`--no-run` is planned) | The `app` container | Environment | `ready_timeout_s` from `up` until the health path answers, on the first clock, then none until cstudy stops it | `sandbox` | [App did not start](#failure-reporting) |
| `test` | `cstudy test`, with the app running | `docker compose exec` in `app` | Environment, plus the visible-only control variables | 120 s | `sandbox` | Its exit code is a test failure; it never grades |
| `reset` | Once with `CSTUDY_RESET_PHASE=prepare` after `bootstrap`, as a one-shot before `app` (in a test or graded stack), then with `CSTUDY_RESET_PHASE=apply` before each case with `fresh: true`, with the app stopped | A one-off app container | Environment | 30 s | `sandbox` | `prepare`: [Migration failed](#failure-reporting). `apply`: case `error`, and the remaining cases `not_run` |
| `grade_setup` | Graded runs and `cstudy verify` only: after services are up and before `bootstrap`. It waits for backing services, so it is proven with them, at P10 | A short-lived container of the same image, with the project folder and `{problem}/grading/` read-only, gone before `app` starts | Environment, plus `CSTUDY_PROBLEM_DIR` and `CSTUDY_GRADED_LEVEL` | Within the startup budget | `sandbox` | A content error, exit 4, whose output is never shown as a hidden case |

`project.timeouts_s` overrides a limit per command: `startup`, `install`, `test` and `reset`.

### Environment

The app container's environment is explicit. **Nothing from your machine is passed on.**

| Variable | Set by | Value |
|----------|--------|-------|
| Everything in `project.env` | The manifest, which [`.env`](#env) is written from | The app's port, stable URLs such as `http://room-vendor:8080`, fake keys |
| `CSTUDY_DATA_DIR` | cstudy | `/data` |
| `HOME`, `TMPDIR` | cstudy | Paths on tmpfs |
| `CSTUDY_MOCK_CONTROL_URL`, `CSTUDY_MOCK_CONTROL_TOKEN` | cstudy, for `test` only | The control interface of a test stack, which holds only visible scenarios. Never set for `run`, and never in a graded stack |

Native problems are a separate matter: their environment is the allowlist of [Process environment](runners.md#process-environment).

### Three boundaries

1. **The core owns the infrastructure.** The generated compose file, hardening, networks, labels and cleanup are cstudy's. A command must not start a service, or leftovers fall apart. Commands run after services are up.
2. **Trust follows location.** `commands` live in the problem's manifest, so you cannot change which commands run. A script in the starter that a command points to can be edited by you. That is acceptable for `install`, `bootstrap`, `run` and `test`, because the grader judges behavior over HTTP: rewriting `bootstrap` only changes the app being judged. It is not acceptable for `grade_setup`, whose script and data must live outside the starter, reached through `{problem}`, the only placeholder an argument list may use, and only in `grade_setup`. It expands to `/cstudy/problem` inside that container. S19 refuses `{problem}` anywhere else and refuses a `grade_setup` that points into the project root.
3. **Existing problems are unchanged.** Every other problem keeps its per-language runner, generated tests and grading, natively, with no Docker.

### How you reach them

| You run | On a service project |
|---------|----------------------|
| `cstudy start <slug>` | Shows what it needs, copies the starter, pulls images, runs `install`, and starts nothing else. It prints `cstudy dev` as the next step |
| `cstudy test` | Starts a test stack, runs `bootstrap` and `run`, runs `commands.test`, then the visible HTTP cases of the unlocked levels as feedback. Nothing is stored and nothing opens |
| `cstudy submit` | The [graded run](#graded-run) |
| `cstudy dev <slug>` (new) | The dev stack, in the foreground, until Ctrl-C |
| `cstudy verify` | Exercises the commands on the reference ([checks](#checks)) |

`cstudy dev` is the only new verb. `install`, `bootstrap`, `run` and `reset` have no verbs of their own. `cstudy test` takes none of the flags of a native run, and exits 3 for one: debug through your own IDE against `cstudy dev`.

```text
cstudy dev [<slug|file>] [--scenario <mock>=<scenario>]...
```

| Flag | Effect |
|------|--------|
| `--scenario` | Sets a mock server's visible scenario at start. A hidden or unknown name exits 3 with the visible names, before anything starts |

It runs in the foreground: it brings the stack up, prints your app's published URL and the mock server names, then what your app prints. Ctrl-C, or SIGTERM, brings the stack down and keeps its data, exit 0, and a second Ctrl-C during that cannot leave half a stack. Your app ending brings the stack down too, exit 2, and so does an app that never starts, with its output. One dev stack runs per project: a second `cstudy dev` exits 3 and names the holder's process id. The lock is `.cs/projects/<slug>.dev.lock`.

Planned, with P9:

```text
cstudy dev [<slug|file>] [--no-run] [--debug] [--reset-data]
cstudy dev [<slug|file>] --exec [--network] -- <command> [<argument>]...
```

| Flag | Effect |
|------|--------|
| `--no-run` | Keeps the `app` container idle instead of running `commands.run`, for an IDE or a debugger. Your app cannot run outside the stack and still reach the mock servers, so running is the default |
| `--debug` | Publishes the template's debug port on `127.0.0.1` |
| `--reset-data` | Removes the dev volume before starting |
| `--exec` | Runs one command in a one-off app container, then exits. `--network` gives it the internet and no stack, which is how you add a dependency: `cstudy dev --exec --network -- pnpm add <package>` |

And one line per request a mock server receives.

## Manifest sketch

Under `project` in `meta.yaml`, in `schemas/meta.schema.json`. `reset`, `grade_setup` and `services` below are what a data-driven problem adds; [the fixtures](#a-small-example) are the smallest that works.

```yaml
kind: project
languages: [typescript]
levels:
  - {level: 1, title: Daily desk passes}
comparator: {type: exact}
project:
  grading: http                 # selects HTTP grading; absent means the entry-class grading of today
  image: node:24-slim@sha256:<digest of the chosen release>
  commands:
    install: [pnpm, install, --frozen-lockfile, --ignore-scripts]
    bootstrap: [node, scripts/migrate.ts]
    run: [node, src/server.ts]
    test: [node, --test]
    reset: [node, scripts/reset-data.ts]
    grade_setup: [node, "{problem}/grading/grade_setup.ts"]
  app: {port_env: PORT, port: 8000, health: /health, ready_timeout_s: 30}
  env:                          # the app's environment; cstudy writes .env from it
    PORT: "8000"
    ROOM_VENDOR_URL: http://room-vendor:8080
    DATABASE_URL: postgres://app:app@db:5432/app
  mocks:                        # at most 4
    - {name: room-vendor, config: mocks/room-vendor.yaml}
  services: services/compose.yaml
  requires:
    lock: pnpm-lock.yaml
    services: [postgres]
    sizes: {install_mb: 40, images_mb: {app: 80, mocks: 50, postgres: 160}, memory_mb: 700}
```

| Field | Rule |
|-------|------|
| `grading` | `http`. It excludes `entry`, `tests`, `clock`, `signature`, generated test files, complexity classes and a `concurrency` block |
| `image` | The toolchain image, pinned by digest. From the problem's template |
| `commands` | The [lifecycle commands](#lifecycle-commands). No other key |
| `app.port_env`, `app.port` | The variable your app reads for its port, and the port, which never varies inside the stack. Your app must read it from the environment and listen on all interfaces inside the container (`0.0.0.0`) |
| `app.health` | A path that answers 2xx when the app is ready |
| `env` | The whole app environment: `port_env`, one URL for each mock server and service your app calls, and fake keys. No real secret. It is the only source of the folder's [`.env`](#env) |
| `mocks` | At most 4, each with a unique `name` (lowercase letters, digits, `-`) that is no service name and none of `app`, `cstudy-mocks` or `cstudy-forward`. Every path is relative to the problem's directory, not the starter |
| `services` | A compose file, relative to the problem's directory ([Backing services](#backing-services)), planned for P10: S21 and S22 check it today, and a stack refuses it |
| `install_env` | What the package manager needs in its install container, such as where its cache is. `/cache` is a volume there |
| `requires` | [What a problem depends on](#what-a-problem-depends-on) |
| `timeouts_s` | `startup`, `install`, `test` and `reset`, in seconds |
| `comparator` | The default for cases: `exact`, `unordered`, `unordered-nested` or `float`, applied to the response body |

## Where the files live

Everything grading trusts lives in the problem's own files, not the starter, so you cannot edit it. `cli/tests/fixtures/service_projects/` holds two small working problems ([A small example](#a-small-example)).

```text
problems/<id>-coworking-availability-typescript/
  meta.yaml
  problem.md
  tests.json
  mocks/
    room-vendor.yaml        # routes and every scenario, visible and hidden
    room-vendor.API.md      # the vendor's visible documentation
    bodies/availability.json
  services/compose.yaml     # a data-driven problem only
  grading/                  # a data-driven problem only: grade_setup and hidden data
  starter/
    README.md, package.json, pnpm-lock.yaml, tsconfig.json, .gitignore
    src/server.ts
    tests/                  # visible tests, and the helper for the control interface
    vendors/room-vendor/API.md    # a copy of mocks/room-vendor.API.md
  solutions/
    explanation.md
    reference/
```

**Vendor documentation.** S20 holds this. The starter holds an `API.md` per mock server, a byte-for-byte copy of the problem's file (S20): base-URL variable, routes, response shapes and a table of visible scenario names. It is a copy for reading, so nothing depends on it and `cstudy start --restore` writes it back. Hidden scenarios appear in neither. A failing hidden case in a practice attempt names its scenario, as a failing hidden case already shows its input ([cstudy submit](cli.md#cstudy-submit)); a mock attempt shows only the count.

## `.env`

No starter holds a `.env`. `cstudy` writes it into your project folder from `project.env` as it copies the starter, an ordinary visible file with no secrets. Mock servers and services have stable names on the stack's network, so nothing in it ever varies, and the manifest stays the only source, so nothing is repeated.

```text
PORT=8000
ROOM_VENDOR_URL=http://room-vendor:8080
DATABASE_URL=postgres://app:app@db:5432/app
```

| Rule | Detail |
|------|--------|
| When it is written | Wherever a starter lands: a new attempt, a resumed attempt whose folder is gone, `--fresh` and review attempts, and `cstudy verify`'s builds of the starter and the reference. A resumed attempt with a folder keeps what is there, as for any file |
| What it is | From then on, a file like any other: tracked, in `code_hash`, in the folder's manifest and in archives, and restored by `cstudy start --restore .env` from what `project.env` says now. A new attempt's `.env` counts as unchanged, so `cstudy status` and a submission never call it your edit |
| Why it exists | Your app's own loader finds what its environment already holds, and you can read how the stack is wired |
| Static check | S15 refuses a `.env` in a service project's starter |
| What it is not | A place for real keys. No problem needs one: a key in `project.env` is a fake, since nothing can reach a real provider from `sandbox` |
| Editing it | It is your file. Nothing reads it to start your app, whose environment is `project.env`, so an edit changes only what your own loader finds. A URL you change that way sends your app elsewhere, and the case fails on the request log |

There is no `.env.local`: with fixed values and no secrets you edit `.env` itself.

## Mock server

One Python program serves every problem and language. For a stack, `cstudy` parses the YAML with the problem and checks it against `schemas/mock.schema.json`, renders it to one JSON document with the stack's control token at `.cs/runs/<stack>/mocks.json`, and mounts that read-only into `cstudy-mocks`, a pinned Python image, with the program's code copied beside it and mounted read-only. The program uses the standard library only, as `adapters/process_liveness.py` does, which has no YAML parser, hence the rendering. The code is `domain/mock_configs.py`.

**Hidden material.** Mock configs reach the mock container only, and only rendered. A dev or test stack's rendering holds visible scenarios only, and a graded one holds them all. A `body_file` is inlined, so no other file of the problem reaches the container, and the body of a hidden scenario goes wherever that scenario goes. Neither the configs nor the token are ever in the app container: a real test looks.

**Names.** Each mock server's `name` is a network alias of the container. The process listens on port 8080 and picks the mock server from the request's `Host`, so `http://room-vendor:8080` needs no port of its own. An unknown `Host` gets a 404 that lists the known names. Nothing is published to your machine.

### The program

In `cli/src/coding_study/adapters/mock_server/`.

```text
python -I <folder> <config.json> [--bind 0.0.0.0] [--api-port 8080] [--control-port 9000]
```

| Item | Rule |
|------|------|
| The folder | Runs alone: its modules import each other relatively and otherwise only the standard library. It may have any name and be read-only, so a stack copies it under `.cs/runs/<run>/` and mounts it |
| Rendered config | One JSON file, `{"control_token": "<token>", "mocks": {"room-vendor": <config>, "second-vendor": <config>}}`, each `<config>` in the [format below](#config-format). The program serves every scenario the file holds: leaving hidden ones out is the rendering's work. It also takes a `body_file`, relative to this file's folder, which it may not leave, and reads it at start; a stack's rendering has inlined each one, so it never meets one there |
| Start | Binds both ports, then prints one line of JSON and serves: `{"api_port": 8080, "control_port": 9000, "mocks": ["room-vendor", "second-vendor"]}`. A bad config exits 2 and a port it cannot bind exits 1, each with its reason on standard error |
| Health | `GET /health` on the control port, with no token, answers `{"status": "ok"}` once both ports are bound. It is not on the API port, where the path belongs to the mocked API. A compose healthcheck: `[CMD, python, -I, -c, "import urllib.request as r; r.urlopen('http://127.0.0.1:9000/health', timeout=1)"]` |
| Stop | SIGTERM and SIGINT exit 0 at once, without waiting for a request in a delay |
| Connections | One thread each, so a delay holds only its own request. At most 24 on the API port, past which a connection waits its turn, because the container's limit is 32 processes; 4 on the control port. Every answer closes its connection (HTTP/1.0), so no idle client keeps a thread. A client that stops sending or reading is dropped after 10 s. On the control port, which your app can reach, a whole request has those 10 s, so one that drips a byte at a time is dropped too, and a request without the token is answered from its head, before any body |
| Request limits | A body up to 1 MiB, past which it is 413 and logged without its body. A chunked body is 411 and a bad `Content-Length` 400. The control port takes 64 KiB |

### Config format

`schemas/mock.schema.json` validates this format.

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
  - id: room-slots
    method: GET
    path: /v1/rooms/{room_id}/slots  # a parameter is a whole segment
    response:
      status: 200
      body: {slots: []}
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
| Matching | Method exact, and path exact except that a `{name}` segment matches any one non-empty segment, whose value is not kept. A repeated query key matches on any of its values. First match wins. No state beyond sequence counters |
| Unmatched | A clear 404 that names the mock server: `{"error": "no route", "mock": "room-vendor", "method": "GET", "path": "/v1/other"}`, and a log entry with `matched: false` |
| Scenarios | The default is no scenario. A scenario overrides the matched response; a field it leaves out comes from the route, and a field it gives replaces the route's whole, `headers` included. So a 429 keeps the route's body unless it says `body: ""`. It never applies to an unmatched request |
| Responses | A mapping or list gets `Content-Type: application/json` unless the headers name one. `Content-Length` is computed unless the headers name one, so a config can lie about it on purpose. 204, 304 and `HEAD` send no body. No `Date` or `Server` header is added |
| Visibility | A scenario is hidden unless `visible: true`, so a forgotten flag cannot leak one. A dev or test stack loads only visible ones |
| `sequence` | One entry per request, in order; the last entry repeats. It stands alone: an entry carries its own fields, `delay_ms` included. Setting a scenario restarts its counter, and a request it does not apply to does not advance it |
| Reset | Sequence counters and the log reset between cases |
| Determinism | Bodies are fixed, with no randomness and no clock, except the [run-time values](#extensions) a config asks for |
| Delays | Hidden cases keep `Retry-After` and `delay_ms` at 1 to 3 s, so they stay under the 10 s [hang guard](runners.md#hang-guard-and-restarts); a case that needs more sets `hang_guard_ms`. `Retry-After` is given in whole seconds |

### Control interface

A token-protected interface that the grader uses. It listens on a port of its own, 9000, so it is not part of the mocked API, and scenario choice is no query parameter that could leak into the vendor's contract. The forwarder publishes it on `127.0.0.1` for the grader and the Web UI.

| Request | Effect |
|---------|--------|
| `POST /reset` | Clears the log and counters, and sets every mock server to no scenario |
| `PUT /mocks/<name>/scenario` with `{"scenario": "outage"}` | Sets a scenario, or `null` for none, and answers what is set. An unknown scenario or mock server is 404 with the known names, and any other body 400 |
| `GET /mocks/<name>/log` | The [request log](#request-log) |
| `GET /health` | [Health](#the-program), the one request that needs no token |

Every other request needs `Authorization: Bearer <token>`, and without it is 401, whatever its path. A known path with the wrong method is 405. No response carries CORS headers, so a page cannot send one. The token is random per stack. The token of a graded stack is never passed to your app, its `test` or any command.

**Inside a graded stack your app can reach this port but has no token.** That is a correctness aid: it keeps an honest app from changing a scenario by accident. It does not stop someone determined to cheat themselves from their own shell.

### Request log

Each entry records what the app sent and what it got.

```json
{"seq": 2, "mock": "room-vendor", "matched": true, "route": "availability",
 "scenario": "rate_limited_then_ok", "method": "GET", "path": "/v1/rooms/availability",
 "query": {"date": "2027-03-01"}, "headers": {"accept": "application/json"}, "body": null,
 "status": 200, "received_ms": 1042, "responded_ms": 1043}
```

An entry appears when its request arrives, with `responded_ms` null until it is answered, so a request still in a delay already counts. `seq` counts requests from 1 after a reset. Times are monotonic milliseconds since the last reset. Header names are lowercase, and a repeated query key's value is a list. Bodies keep 64 KiB, with `truncated: true` beyond that, and one that is not UTF-8 goes in `body_base64` instead, with `body` null.

Reading a log answers `{"mock": "room-vendor", "entries": [...], "truncated": false, "dropped": 0}`. A log keeps 1,000 entries per reset and 8 MiB of bodies, headers, paths and queries per mock server, since 1,000 full bodies would not fit the container's 64 MiB. Past a limit it keeps its first entries, and `truncated: true` and `dropped` say how many it did not. The requests themselves are still answered. Query strings count toward the 8 MiB too, since 1,000 requests with 64 KiB queries would pass the container's limit as well.

### Extensions

Recommended, to confirm (R33), for P11. They let a config mock a streaming API, an LLM provider among them.

```yaml
shape_version: "2026-11"             # the shape this config records, for a real API's shape
routes:
  - id: completion-stream
    method: POST
    path: /v1/completions
    match: {body: {stream: true}}    # a JSON subset of the request body
    response:
      status: 200
      headers: {Content-Type: text/event-stream}
      stream:
        - {data: '{"id": "{{request.body.request_id}}", "delta": "Desk "}', after_ms: 20}
        - {data: '{"delta": "passes"}', after_ms: 20}
        - {data: "[DONE]"}
scenarios:
  dropped_mid_stream:
    visible: true
    route: completion-stream
    drop_after_chunks: 1             # closes the connection with no terminator
```

| Feature | Rule |
|---------|------|
| SSE streaming | `stream` lists chunks, each with `data` and `after_ms`. `drop_after_chunks` in a scenario closes the connection mid-stream |
| Matching on bodies | `match.body` is a JSON subset, or `match.body_contains` a string. Listed before a route that does not match on bodies, since the first match wins |
| Logged bodies | A case's `log` entry gains `body`, a JSON subset the logged body must contain, and `body_prefix_stable: true`: each request's body bytes start with the previous request's whole body, which is what a cache-stable history needs. A body truncated at the log's limit is a content error for that assertion, so such a route raises its own limit up to 1 MiB |
| Run-time values | `{{request.*}}` from the current request, `{{seq}}` for the mock server's request counter, `{{now_s}}` for the clock. Cases never compare them literally, and D11's determinism run covers what remains |
| A mock LLM provider | Just config data on this format, with no key and no cost. A fake key goes in `project.env`, and a `log` entry can assert the header carried it |
| Shape drift | Provider response shapes drift, so a config modeling a real API records `shape_version`, an authoring rule that no check can detect. It is a record for authors, and cstudy never checks it against a live API |
| Out of scope | Per-request token signing for a mock identity provider. Use a service container, decided at the first identity problem (R34) |

## Backing services

Planned, for P10. S21 and S22 check a compose file today, and a stack refuses a problem that declares one.

Docker is how service projects get backing services such as Postgres, Redis and LocalStack. A problem with none still runs in Docker, and a problem may keep SQLite in `CSTUDY_DATA_DIR`.

The compose file belongs to the problem, so you cannot edit what grading trusts, and it is tool-neutral, so any image can be used. It holds only services. cstudy adds the networks, labels and limits it requires.

```yaml
services:
  db:
    image: postgres:17@sha256:<digest of the chosen release>
    environment: {POSTGRES_USER: app, POSTGRES_PASSWORD: app, POSTGRES_DB: app}
    mem_limit: 512m
    pids_limit: 256
    healthcheck:
      test: [CMD-SHELL, pg_isready -U app]
      interval: 1s
      retries: 30
```

Your code reads `DATABASE_URL`, `REDIS_URL`, `AWS_ENDPOINT_URL` or whatever the problem names, from `project.env`, reaching the service at its stable name such as `db:5432`. A service publishes no port. To look inside it, use `docker compose exec` on the printed project name.

## Databases

Planned, for P10.

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

The script and its files never enter the `app` container. The rows it loads do reach the database your app reads, which is inherent in this design.

### Contract tables

A design point. For live-read checks, where the service must see a change made behind its back, a problem may declare tables as a stable contract that the grader writes to mid-run and that you may not rename:

```yaml
project:
  contract_tables: [member_credits]
```

A case then names a problem-owned script as `write_data`, run as `grade_setup` is. **A contract table limits your schema freedom**, so the statement names it, and a problem uses one only when neither the API nor a mock server can make the change.

### Reset

Data resets per run. A problem that needs a reset between cases declares `commands.reset`, and a case asks for it with `fresh: true`. cstudy stops the app, runs `reset` with `CSTUDY_RESET_PHASE=apply`, and starts the app again. `CSTUDY_RESET_PHASE=prepare` runs once after `bootstrap`. PostgreSQL's `CREATE DATABASE ... TEMPLATE` is an example of such a command, not a core feature, and its cost is measured when first used. Without `commands.reset`, `fresh: true` only restarts the app.

### Parallel cases

Planned, for P10. A case type for N requests against limited capacity. It gives language-neutral concurrency grading, which is what SQLite cannot show, since a row lock and a lost update need a database that serves writers at once.

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

One piece of core code covers every language, with no per-language runner work. No runner job is involved. Existing entry-class problems keep their path. The grader runs on your machine, outside every container, and reaches your app and the control interface through the forwarder's published ports, so hidden cases never enter a container.

### The code

Step 6 of the [graded run](#graded-run), as a use case that is handed a ready stack: `run_http_grading` in `application/http_grading.py`, with `domain/http_case.py`, `domain/http_grading.py` and `adapters/http_grader/`. It returns a `Judgement`, so levels, submissions and events are today's. `application/service_grading.py` brings its stack up and `application/graded_stack.py` adapts that stack.

The grader asks a stack for little, through `GradedStack` in `application/http_grading_ports.py`:

| Member | What it is |
|--------|------------|
| `endpoints` | `app_url` and `control_url` on `127.0.0.1`, `control_token`, and the names in `mocks`. `control_url` is `None` without mock servers |
| `restart_app()` | Stops your app and starts it again, for a case that hung it |
| `restart_app_with_fresh_data()` | For `fresh`: stops your app, runs `commands.reset` with `CSTUDY_RESET_PHASE=apply` if declared, starts your app |
| `app_exit(within_ms)` | Your app's exit code and stderr tail, or `None` if it still runs after waiting that long, since a container's exit shows a moment after its connections drop |

Both restarts return once the health path answers again, and raise `StackStepError` otherwise.

### Two clocks

Every time limit and hang guard starts only once the stack is ready (owner, O17). Starting it, and each restart above, runs on the first clock and counts toward no case. Its budget is generous, 300 s for `up --wait` unless `project.timeouts_s.startup` says otherwise and `app.ready_timeout_s`, 60 s by default, for the health path after that, and running out of it says so with its own message and changes no result.

A case's limit runs from its first request to the last byte of its last answer, `before` requests included. It holds for the whole exchange, so an app that sends a byte now and then cannot outlast it. The limit on `commands.test` starts at ready as well, and the times `cstudy test` and `cstudy submit` report leave startup out, showing it apart as `not counted`.

### Graded run

`cstudy submit`, and D1 and D3 of `cstudy verify`:

1. Check `requires` and the install record; pull images and install if needed.
2. Render the configs, with every scenario, and generate the compose file.
3. With `grade_setup`, planned with it at P10, the from-empty check: bring up the mock and service containers, run `bootstrap` on empty data, then discard the data (`down -v`). Without `grade_setup`, the `bootstrap` of the next step is itself this check.
4. Bring up a fresh stack (`up --wait`), with its one-shots in order before `app`: `grade_setup` if declared, `bootstrap` if declared, `reset` with `prepare` if declared. The app's start depends on them and on the mock container being healthy, which P1 measured faster than separate steps, with one failure path.
5. `app` runs `commands.run`. Poll the health path through the published port until 2xx or `ready_timeout_s`, each try limited to 5 s as a whole, so an answer that never ends still counts as no answer. The second clock starts here.
6. For each case of the graded levels, in `tests.json` order: `POST /reset`; if `fresh`, restart with fresh data and `POST /reset` again, so your app's startup meets no scenario left by the last case and the log holds this case's requests alone; set scenarios, send `before` requests or `steps`, send the request, compare, assert on the log.
7. `down -v`.

Each `cstudy submit` has a stack of its own, under a fresh name, so two at once cannot collide, and `.cs/runs/` holds the run's generated files until it ends. A case past its limit is `timeout` and restarts your app, as a runner restarts ([hang guard](runners.md#hang-guard-and-restarts)); after 3 such cases the remaining cases are `not_run`. An app that exits during a case does not restart: the case is `error`, it says so with the exit code and the stderr tail, and the remaining cases are `not_run`, since a crash usually repeats and each case would pay for it. A connection that fails while your app runs is `error` for that case alone. The limit per case uses the same order as a runner's: config `hang_guard.ms`, the case's `hang_guard_ms`, `limits.hang_guard_ms`, else 10 s.

### Hidden HTTP case

Language-neutral, in `tests.json`, with `id`, `visible`, `level`, `note` and `hang_guard_ms` as today. An example that asserts the app waited for `Retry-After` and did not hammer the vendor:

```json
{"id": "h14", "level": 3,
 "note": "a 429 from the room vendor: wait for Retry-After, then retry once",
 "mocks": {"room-vendor": "rate_limited_then_ok"},
 "request": {"method": "GET", "path": "/availability", "query": {"date": "2027-03-01"}},
 "expected": {"status": 200,
              "body": [{"product": "desk_pass", "date": "2027-03-01", "available": 12},
                       {"product": "meeting_room", "room": "oak", "slots": ["09:00", "10:00"]}]},
 "comparator": {"type": "unordered"},
 "log": [{"mock": "room-vendor", "route": "availability", "count": 2, "min_gap_ms": 950}]}
```

| Field | Rule |
|-------|------|
| `mocks` | The scenario per mock server; a mock server it leaves out has none. A visible case names visible scenarios only (S23) |
| `before` | Requests sent first, each of which must answer 2xx, for a case that needs state. They share the case's limit, and the one that fails names itself in the reason. Optional |
| `request` | `method`, `path`, optional `query`, `headers`, and `json` or `body`. A `query` value is a string, or a list sent once per value. `json` is encoded and sends `Content-Type: application/json` unless `headers` name one. `body` goes out byte for byte, so it can be malformed |
| `expected.status` | Required |
| `expected.body` | Optional; left out, any body passes. A string is the body's exact text. Anything else is compared parsed, by `comparator`, so key order and whitespace cannot fail a correct answer, and `null` asks for a JSON null. An object must hold exactly the fields expected: an extra one fails and is named. `NaN` and `Infinity` are not JSON |
| `expected.headers` | Optional. Each listed header must match, its name in any case. A `Content-Type` that names no parameter ignores the answer's, so a framework's `; charset=utf-8` cannot fail it |
| `comparator` | Overrides the problem's: `{"type": ...}`, with `tolerance` for `float`. `exact`, `unordered`, `unordered-nested` or `float` ([Comparators](problem-format.md#comparators)). `checker` is not allowed |
| `log` | Assertions per mock server and route: `count`, `min_count`, `max_count`, and `min_gap_ms`, measured from each response's `responded_ms` to the next request's `received_ms`. Without `route`, they cover every request the mock server logged, matched or not, and requests past the log's limit still count. A log that overflowed fails an assertion with a `route` or a `min_gap_ms`, saying so: `dropped` says how many came and not which route they took or when, and the retry too soon may be the very one it did not keep. A value a little below the wait, here 950 for 1 s, tolerates timers |
| `fresh` | Restart the app and run `commands.reset` first |

A case has a `level`, or no graded run would reach it. `project.clock: virtual` is refused with `grading: http`: these cases run on the real clock. The bound on waits and D11 keep them stable.

A case that names a mock server the stack lacks, or a scenario a mock server lacks, or a problem whose comparator is `checker` or `ops` with no override, is a content error rather than a verdict. S23 catches these first.

### Multi-step cases

Recommended, to confirm (R34), for P11. A later request can use values captured from earlier responses, for login and OIDC flows. A case has either `request` or `steps`.

```json
{"id": "h30", "level": 2, "note": "a session token works only after login",
 "steps": [
   {"request": {"method": "POST", "path": "/login", "json": {"member": "m1"}},
    "expected": {"status": 200},
    "capture": {"token": "body.token", "next": "header.location"}},
   {"request": {"method": "GET", "path": "/me",
                "headers": {"Authorization": "Bearer {{token}}"}},
    "expected": {"status": 200, "body": {"member": "m1"}}}]}
```

| Rule | Detail |
|------|--------|
| `capture` | A name per value: `body.<dotted path>` or `header.<name>`. A missing value fails the step, and the reason names it |
| Use | `{{name}}` in a later step's `path`, `query`, `headers`, `json` or `body`. `{i}` stays the parallel case's index, and `{problem}` the command placeholder |
| Client | No redirect is followed, so a flow asserts each one. Cookies are kept across the steps of a case |
| Verdict | A case passes when every step does. A failing case in a practice attempt names its step |

### What you see

`--json` and `--events` keep version 1 of the [event stream](cli.md#event-stream), with additive changes only, so the CLI and the Web UI render it:

| Event | On a service project |
|-------|----------------------|
| `output` | Progress: image pull, install, Docker start, `bootstrap` |
| `test_start`, `test_result` | Planned, with P9's Web UI: `cstudy test --events` and `--json` exit 3 on a service project for now. One result for `commands.test`, with id `commands.test`; its output streams through `output`, since cstudy does not parse a framework |
| `case_start`, `case_result` | `cstudy submit`, and with `--events` above also `cstudy test` for the visible cases. `input` holds the request and the scenarios it set, `expected` and `actual` the status and body, and `reason` every difference and log assertion that failed (`room-vendor availability: expected 2 requests, saw 5`) |
| `level_result`, `level_unlocked` | As today, with `methods` empty |

A hidden case in a mock attempt writes no event, as today.

A report cuts `expected` and `actual` at 200 characters, so `reason` names what differs by its path in the body, showing only those values (`body.rooms[0].slots[1]: expected "10:00", got "11:00"`), up to 5 differences. Two long texts show the part around where they first differ. An `unordered` body names the elements missing and unexpected. A wrong status says only that, since an error's body differs anyway, and `actual` shows it.

| What happened | `status` | The case's entry says |
|---------------|----------|-----------------------|
| A wrong status, header or body, or a failed log assertion | `fail` | `reason`, with each one found |
| No whole answer within the limit | `timeout` | `hang_guard_ms` |
| Nothing listening on your app's port, while your app runs | `error` | `error.type` `ConnectionRefused` |
| The connection dropped before a whole answer, while your app runs | `error` | `error.type` `ConnectionDropped` |
| Your app exited | `error` | `error.type` `AppExited`, the exit code, and the stderr tail in `error.trace`. The remaining cases are `not_run` |
| `commands.reset` or the restart around it failed | `error` | `error.type` `ResetFailed`, with its output in `error.trace`. The remaining cases are `not_run` |
| An answer that is not HTTP, or a body over 8 MiB | `invalid` | `reason` |

A `not_run` case's reason names no earlier case, so a mock attempt's hidden cases stay hidden.

## Dependencies

A project problem may have its own dependencies, and cstudy installs them automatically (owner, R1).

### Install rules

| Rule | Detail |
|------|--------|
| When | At `cstudy start`, with progress. A resumed attempt, `cstudy test`, `cstudy submit` and `cstudy dev` install again when the lock file's digest differs from the record, or what it installed is gone |
| Where | A one-off app container in a compose project of its own, on an ordinary bridge, hardened as every container is, with the project folder and the install cache mounted and nothing else |
| Record | `.cs/projects/<slug>.install.json`, with the lock's SHA-256, written after success |
| Lock | The project's exclusive [lock](installation-and-workspaces.md#project-folders) is held during an install |
| Retry | A failed install keeps the attempt. It prints the retry, `cstudy start <slug>`, and the Web UI offers a Retry button |
| You add a dependency | From a shell of your own for now, and `cstudy dev --exec --network -- <your package manager's add command>` once it is built. The digest differs, so the next command installs. The lock file is your file, hashed in `code_hash` |

### Templates per language

The per-language table lives in project templates under `cli/src/coding_study/adapters/templates/`, as `project-<language>-service/`. A new language means a new template and one row in `PROJECT_TEMPLATE_LANGUAGES` in `domain/scaffold.py`, with no new core logic. Only TypeScript and Python are settled, for the first problems. The others are settled when reached.

| Language | `install` | `run`, `test` | State |
|----------|-----------|---------------|-------|
| TypeScript | `corepack pnpm install --frozen-lockfile --ignore-scripts`, with `packageManager` pinning pnpm in `package.json` and `COREPACK_HOME` and `npm_config_store_dir` in the cache volume | `node src/server.ts`, `node --test` | Settled: `node:24-slim`. `typescript` stays below 7 until it is checked, since the broker needs `tsserver.js` |
| Python | `uv sync --frozen --no-build`, with a real `.venv`, not the link to the shared venv, `UV_CACHE_DIR` in the cache volume and `UV_PYTHON_DOWNLOADS=never` | `.venv/bin/python src/server.py`, `.venv/bin/python -P -m pytest` | Settled: the uv image, `python3.13-bookworm-slim` |
| Kotlin, Java | To settle at P12 | To settle | Conflict: Gradle runs `--offline` in [project builds](runners.md#jvm-project-builds) |
| Go | To settle at P13 | To settle | Conflict: `GOPROXY=off` and vendored modules ([ADR 0012](../decisions/0012-go-and-rust.md)) |
| Rust | To settle at P14, if reached | To settle | Conflict: vendored crates and `cargo --offline` ([ADR 0012](../decisions/0012-go-and-rust.md)) |

Those conflicts are template decisions for these problems, and the existing project paths keep what they do.

### Lock files and static checks

S15 today rejects dependencies in a starter and rejects lock files ([starter](problem-format.md#starter)). For a service project that flips:

- A lock file is required when `requires.lock` is declared, and the install must use it exactly. Because a command's content is free, the rule is checked by what it does: D11 fails when `install` changes the lock's digest.
- The starter's limit of 50 files and 256 KiB may not fit a lock file, so lock files are excluded from it.
- `is_untracked` names `uv.lock` and `Cargo.lock`, the workspace `.gitignore` ignores `projects/*/uv.lock` and `projects/*/Cargo.lock`, and an archive deletes them. For a service project the lock is tracked, hashed and archived, and the starter's own `.gitignore` re-includes it.
- A Python starter has a `[project]` table and `requires-python`, which S15 refuses today because of the `.venv` link. A service project has no link, so `cstudy start` writes none and `cstudy doctor --fix` restores none.

**Install scripts.** Off, in every install: `--ignore-scripts` for pnpm, and `--no-build` for uv, which S19 holds a problem to. A problem's dependencies are ones with no native build, because a native package is built for the container, not for your machine, and a package that needs a build fails its install.

### Authoring guidance: migration tools

A migration tool is chosen at authoring time and counts as a project dependency under these rules: it must be pinned and it must run with no network after `install`. This is guidance for any problem that picks it, not a requirement of cstudy.

**Liquibase**, the owner's preference and neither a default nor a requirement. Checked on 2026-11-05 against [Liquibase's 5.0 release notes](https://docs.liquibase.com/community/release-notes/5-0) and [its license announcement](https://www.liquibase.com/blog/liquibase-community-for-the-future-fsl):

| Fact | Consequence for a problem |
|------|---------------------------|
| Community 5.0 and newer need Java 17 or newer | On a Kotlin or Java problem the JVM is already in the image. On a TypeScript, Python, Go or Rust problem the problem's image must hold Java too, which a larger image and `requires.sizes` show. Nothing is needed on your machine |
| The distribution no longer bundles drivers or extensions; they are added through `liquibase lpm` or Maven | Whether a SQLite driver is available this way is unverified: confirm at authoring |
| Community 5.0 and newer are under FSL-1.1-ALv2, which Liquibase states is not OSI open source and which converts to Apache 2.0 two years after each release; versions before 5.0 stay Apache 2.0 | Choose the version line to pin with the license in mind, per problem |
| A JVM start adds time and memory to each `bootstrap` | Not measured. Measure at authoring |

Liquibase's contexts or labels are one way to separate seed changesets, and to apply only the baseline in `grade_setup`. Verify this before relying on it.

## What a problem depends on

The CLI and the Web UI list what a problem depends on, so you know before starting. This extends the display of [ADR 0016](../decisions/0016-jdk-range.md) rather than adding a parallel concept: today a [JDK range](cli.md#the-selected-jdk) marks a language with `!` and a footer in `cstudy list`, names a declared range in `cstudy show`, refuses `cstudy start` with exit 4 and a `fix:` line, disables a language in the Web UI's [Start dialog](web-ui.md#problem-view) with the same reason, and appears as `jdk` in `cstudy list --json`.

| Shown | Source |
|-------|--------|
| Docker | Every service project |
| Language and toolchain version, with image download size | The problem's language, `project.image` and `requires.sizes`. Your machine needs no toolchain for it |
| Each service, with image download size | The compose file and `requires.sizes` |
| Mock servers, by name; they need nothing from you beyond the mock image | `project.mocks` and `requires.sizes` |
| Package manager and approximate install size | The lock file's name and `requires.sizes` |
| Total download and approximate memory | `requires.sizes` |
| Whether each is met here, with the reason when it is not | The same checks as `cstudy doctor`, at the moment it is displayed |

### Where it comes from

The list is a small declared `project.requires` block plus what cstudy derives from the compose file and lock file. A static check (S22) fails when the declared list disagrees with those files, so it cannot drift. `cstudy verify` measures the install's size and D11 fails when it is more than 25% from `requires.sizes.install_mb`. It does not write it, since cstudy never writes to the content root except through `cstudy new`: it prints the measured value for the author to copy. Image sizes and memory are declared and shown, and measuring them is planned: what `docker image inspect` knows is the unpacked size, and memory depends on what else the engine holds.

### Where it shows

| Surface | What |
|---------|------|
| [`cstudy list`](cli.md#cstudy-list) | A `NEEDS` column, only when a listed row has a value: `docker`, or `docker postgres`. Content only: it runs no process, as ADR 0016 rejected a `java -version` per command against NFR-2's 500 ms |
| `cstudy list --needs` | `--needs none` keeps problems that need nothing beyond the language's toolchain, which leaves out every service project; `--needs docker` or a service name keeps those that do |
| `cstudy list --json` | Each entry gains `requires`, next to `jdk`, null for other problems |
| [`cstudy show`](cli.md#cstudy-show) | The full list above the statement, with each requirement's state. It reads state and starts nothing |
| [Problems view](web-ui.md#problems-view) | Planned, P9: the marker in the table and a filter of the same values |
| [Problem view](web-ui.md#problem-view) | Planned, P9: the full list |

An example, with illustrative figures:

```text
needs
  docker     running engine and compose v2         WARN  not installed · <install message>
  language   typescript · node 24 in its image, 80 MB download
  packages   pnpm · about 40 MB installed
  services   postgres · 160 MB download
  mocks      room-vendor · mock image, 50 MB download
  total      about 300 MB download, about 700 MB memory
```

### At Start

`cstudy start` and the Web UI's Start show the summary before any download begins. They ask for confirmation only when something will be downloaded or a requirement is missing. `cstudy start --yes` skips the prompt for scripts; without a terminal and without `--yes`, a start that would download exits 3 and names the flag. If a requirement is missing, Start says what to install rather than failing midway, exiting 4 before it writes anything, as a JDK outside the range does. A stopped Docker engine is not missing: Start starts it ([Docker states](#docker-states)).

## Without a network

After the install and the image pull, a service project runs with no internet: everything talks over the stack's network, and the network itself stops `bootstrap`, `run`, `test` and `grade_setup` from reaching anything else. If the install has not happened and there is no network, cstudy says so rather than showing a raw error:

```text
coworking-availability-typescript needs its dependencies, and the install could not reach the network.
Connect to the network, then run: cstudy start coworking-availability-typescript
```

## Failure reporting

| Failure | Report | Exit, `--json` outcome |
|---------|--------|------------------------|
| Install failed | The command, the tail of its output, and the retry | 4, `error`. Attempt kept |
| Docker missing, stopped and could not start, or no permission | The state's message ([Docker states](#docker-states)) | 4, `error` |
| Service failed: `up --wait` timed out or an image cannot be pulled | The container, its log tail, and the retry | 4, `error` |
| Config error in a mock config, the compose file or the manifest | The file and the reason, as a content error; S19 to S21 catch it first | 4, `error` |
| Migration failed (`bootstrap`) | As an install failure: the command and its output tail, except in a mock attempt, where only that it failed on existing data. In `cstudy submit` it is your code, so the submission is stored, as a [load failure](cli.md#cstudy-submit) is | 2, `load_failed` |
| `grade_setup` failed | That the problem is at fault, without its output | 4, `error` |
| App did not start: it exited | The exit code and the tail of its standard error, at most 4 KiB | 2, `load_failed` |
| Health timeout | The URL, the time limit, the stderr tail, and a reminder to read `port_env` and listen on all interfaces inside the container (`0.0.0.0`), not `127.0.0.1` | 2, `load_failed` |
| App ran out of memory | That the container hit its `mem_limit`, and the limit | Case `error`, or 2 at start |
| App died during a case | Case `error`, with the exit code and the stderr tail; the remaining cases `not_run`, with no restart | 1, `failed` |

## Resources

| Resource | Expectation |
|----------|-------------|
| Graded runs | One stack per run |
| Mock server memory | The container is limited to 64 MiB. P1 measured a stand-in at 15 MiB, and the program alone held about 29 MB after starting, on macOS on arm64 with two mock servers |
| Disk per project | `node_modules` or `.venv`: 27 MB for the TypeScript problem, measured at P7, and P8 for Python; plus images and the install cache, shared across projects |
| Container output in memory | What a container prints is as long as it likes, and `cstudy dev` follows an app with no time limit. So `cstudy` holds the last MiB of a command's output, each line goes by as it comes, and a line with no newline comes in pieces of 64 KiB |
| Docker | [Resources and CI](#resources-and-ci) |
| Language servers | Each project still counts toward `cstudy serve`'s limit of four language servers |

### Cleanup

There is no `cstudy reset` and no command that removes a problem; verified against `entrypoints/commands/`.

| Action | What it removes |
|--------|-----------------|
| `cstudy start --fresh`, or a review attempt | `archive_folder` runs `remove_untracked` first, so `node_modules`, a real `.venv`, and caches are deleted, not archived. The next start installs again |
| Deleting `projects/<slug>/` by hand | Everything in it. A resumed attempt copies the starter and installs again |
| `.cs/build/projects/<slug>/` | The reference's copy and its install, recreated by `cstudy verify` |
| `cstudy doctor --fix` | Docker leftovers, by label only |
| `cstudy dev --reset-data` | The dev volume |
| Images | Never removed by cstudy, since other work may use them |

## Code intelligence and editors

**The riskiest part of the design.** The spike measured that it works, close to the host's speed. It is planned for P9.

### Language servers

Planned, for P9 (R28). Until then a service project has no language server at all: sandboxed code writes its folder, and basedpyright or tsserver on your machine would read it. A session is refused as for a language with no server, 422 `usage` with `no code intelligence for python yet`. The page still tries one, since `installed` is per language, and shows `reconnecting…`, then `stopped · Restart`, until P9 tells it. With P9, a language server runs in a small `lsp` sidecar through `docker exec -i`, the same Node image for both languages, `network_mode: none`, with the project and `.cs/lsp/` mounted, and paths matching because of the same-path mount. A language server must not read a mock config or a hidden case, and inside the container there is nothing to hide: none of them are mounted. ADR 0018's four [hidden directories](web-ui.md#hidden-directories), `.cs/build/`, `.cs/cases/`, `.cs/runs/` and the content root, do not exist there.

| Item | Where it is | Covered by |
|------|-------------|------------|
| Mock configs, compose files, `grading/`, `tests.json` | The problem's files | Not mounted in `app` |
| A graded run's generated files and rendered configs | `.cs/runs/<run>/` | Not mounted in `app`; rendered configs in `cstudy-mocks` only |
| A reference's copy and install | `.cs/build/projects/<slug>/` | Not mounted, unless it is the folder under `cstudy verify` |

What the spike answered:

- **Where the server comes from.** `.cs/lsp/` mounted read-only in the sidecar. basedpyright needs no Node in a Python image then.
- **Which container.** The sidecar, not the app's, since TypeScript alone took 468 MiB of anonymous memory.
- **Stopping it.** Killing the `docker exec` client stops both servers, because they exit on end of input.
- **Definitions outside the folder.** None in the sidecar design, for these two servers.

Otherwise service projects use existing roots: the session's root is the project folder, basedpyright resolves imports through the folder's `.venv`, and tsserver through its `node_modules`. Non-Node servers come with their languages' phases.

### Your own IDE

Planned, for P9 (R29).

| Item | Rule |
|------|------|
| IDEs | The user's own IDE probably uses a generated `devcontainer.json`, naming the same image, mount and network, written by `cstudy dev`. VS Code and IntelliJ read it. LazyVim does not, so the spike tries a per-project server command there |
| Debugging | `cstudy dev --debug` publishes the template's debug port on `127.0.0.1`, for Node's inspector or debugpy. Paths match because of the same-path mount |
| A host toolchain | Not needed. An editor running its own server on your machine finds `.venv` pointing at an interpreter that exists only in the container, and native packages built for Linux |

## Web UI

| Item | Phase |
|------|-------|
| A stack starts only on request from the attempt page, because of its memory, and stops with the page, with the same idle rule as [language servers](web-ui.md#lifecycle-and-limits) | P9 |
| Stack and mock server status, and a scenario picker over the control interface | P9 |
| `.env` is an ordinary file in the tree | P4, built |
| The dependency list, and Start's summary and confirmation | P9 |
| The Docker messages in Start and the [Health view](web-ui.md#health-view) | P9 |
| Code intelligence through the [container](#language-servers) | P9 |

If a terminal holds the dev stack, the page shows that and does not start a second.

## Checks

### Static

| Check | Rule |
|-------|------|
| S5 (changed) | An example marks a visible case with `<!-- case: <id> -->`, in the `## Level` it belongs to |
| S14, S15, S16 (changed) | With `grading: http`: no `entry`, `tests`, `clock`, `signature` or generated-test rules, and no `ops` comparator rule. A track other than `practical` is allowed ([ADR 0020](../decisions/0020-catalog-labels.md#rule-changes)). The starter holds `README.md` and its lock file, and no `.env` or `.env.local`, since `cstudy` writes `.env` from `project.env`. S15's rules on `package.json`, `pyproject.toml` and lock files [flip](#lock-files-and-static-checks). A `request` in a case belongs to a service project |
| S19 (new) | `commands` holds only the standard names; `run` and `test` are declared, `install` with `requires.lock`, `bootstrap` with `services`; each is a non-empty list of strings; `{problem}` only in `grade_setup`, whose script lies outside the starter; `image` pinned by digest; `app` complete; `env` holds `port_env` with `app.port`; a URL in `env` names a declared mock server on 8080 or a declared service; at most 4 mock servers with unique names, none reserved |
| S20 (new) | Every mock config valid against `schemas/mock.schema.json`, as the problem loads; a config lies in `mocks/`; `body_file` stays inside `mocks/`, exists and is text; every scenario's `delay_ms` and `Retry-After` are at most 3 s, and `Retry-After` is whole seconds; `room-vendor.API.md` and its starter copy at `vendors/room-vendor/API.md` are byte-identical and list every visible scenario and no hidden one |
| S21 (new) | The compose file holds only `services` and their `volumes`, with images pinned by digest and no `build`; no `ports`, `networks`, `network_mode`, `restart`, `container_name`, top-level `name`, `privileged`, `cap_add`, external volume, Docker socket, anonymous volume or bind mount outside the problem; `mem_limit`, `pids_limit` and `healthcheck` on every service; no service takes a reserved name or a mock server's |
| S22 (new) | `requires` agrees with the compose file, the lock file and `commands`: `services` names the images' repositories, `lock` exists and `images_mb` has a row per image |
| S23 (new) | Every HTTP case: levels numbered from 1, a level of its own, and every level with a case; `mocks` names known scenarios, visible ones only in a visible case; `log` names known routes; `fresh` with data needs `commands.reset`; a comparator that can judge a body; waits within the case's hang guard. Planned with their cases: `count` from 2 to 64, and a step's `{{name}}` was captured by an earlier step |

### Dynamic

| Check | Rule |
|-------|------|
| D1 (changed) | The starter: `install` and `bootstrap` succeed, `run` answers the health path, a graded run of level 1 reports a result for every case (cases may fail), `test` runs without crashing: it may fail, and it may not time out or fail to start |
| D3 (changed) | The reference passes every HTTP case through the [graded run](#graded-run), as the starter with its overlay |
| D9 (changed) | The reference: `commands.test` exits 0, and the visible cases pass. No generated test files exist |
| D7 (extended) | Planned with parallel cases, P10: a broken overlay passes every sequential case and fails each parallel case in its `caught_by` |
| D11 (new) | `install` leaves the lock's digest unchanged; `bootstrap` succeeds from empty and twice in a row; three runs of the reference give the same verdicts; the slowest case stays within 50% of its hang guard; the install is within 25% of `requires.sizes.install_mb`; a probe on `sandbox` reaches no public, LAN or metadata address. Outside NFR-3's 30 s per problem, as D6, D7 and D10 are |

Without a usable engine, `cstudy verify` skips a service project with the reason, as a JDK out of range does, and `--require-ready` counts that as not passed. `--static` asks the engine nothing.

### Ready rules

The [ready rules](authoring.md#ready-criteria) can be met with these changes:

| Rule today | Change |
|------------|--------|
| At least 2 visible and 2 hand-written hidden cases per level, at least 8 hidden in all | Kept. Four levels already give 8. Visible cases feed the statement's examples and `cstudy test` |
| Exactly one approach, `optimal`, with its overlay and `### Design` | Kept, with no complexity classes |
| A starter with `README.md` | Kept, and it also names how to run the app and which variables it reads |
| D9 passes | Its meaning changes, as above |
| S5: examples per level, generated `Methods to add` | Examples render a request and a response. A level names the endpoints to add |
| New | D11 passes. A data-driven problem also has a baseline, its `grade_setup` runs, and a from-empty `bootstrap` passes. A problem with parallel cases has a broken overlay caught |

## A small example

`cli/tests/fixtures/service_projects/` holds two working problems, one in TypeScript and one in Python, for the tests on a real engine. They are the smallest that use everything built: a mock server, `bootstrap`, `reset`, levels, hidden cases with the 429 scenario, a reference and a naive solution that a hidden case catches. They are no catalog problems.

## Unproven on Linux

Nothing here has run on Linux. The `sandbox` CI job is what will show it, on its first push. What may differ:

| Item | Why |
|------|-----|
| `internal: true`, the forwarder, the egress probe | A real firewall on the host in place of Docker Desktop's proxy. Whether a sandbox container reaches the host at its bridge address needs its own probe |
| `host.docker.internal` | Not defined by default on Linux, so what `install` reaches there differs |
| File ownership | **The biggest gap**, because Docker Desktop hides it: UIDs are real on Linux, for the tmpfs options, the one-off `chown`, setuid bits, and whatever a root one-off leaves in the project. Clearing a setuid bit changes a mode without following a link, which an older glibc cannot do: the bit then stays |
| SELinux labels, rootless Docker | Not exercised |
| Starting the engine, and the "no permission" state | `systemctl` and a printed `sudo` command are untested |

## The first problem

Original to cstudy ([ADR 0004](../decisions/0004-original-problem-wording.md)). A coworking space sells hot desks, counted per day in its own data, and meeting rooms, in time slots from outside vendors. One API serves both. It is built in TypeScript as `problems/0277-coworking-availability-typescript/`, with `coworking-availability-python` to follow, each a separate problem as [ADR 0014](../decisions/0014-project-problems.md) requires.

| Level | What it asks |
|-------|--------------|
| 1 | `GET /desks` already answers the count for a day on sale. Give it the right answers to a wrong request, so the starter passes 4 of its 14 cases and `cstudy done` keeps its meaning |
| 2 | `GET /availability`: one answer with the desks and `room-vendor`'s open slots, flattened and sorted |
| 3 | Vendor failure handling: a 5xx, a 429 with and without `Retry-After`, a slow answer and a broken body. Desks are still answered and the vendor is named in `unavailable`, with retries bounded and the request log checking the count and the gaps |
| 4 | `annex-vendor`, a second mock server with another shape and its own failures, among them an error in the body of a 200. One vendor failing touches nothing of the other's |

The stack is `node:http` and `fetch`, with no runtime dependency, so the install is the same 27 MB as the fixtures'. There is no database: the seeded counts are a file in the starter, so the problem declares neither `bootstrap` nor `reset`. Every level is graded again on each submit, so `/desks` stays a separate endpoint, a slot names its vendor from level 2, and `unavailable` is a list from level 2, which lets an earlier level's cases hold once the annex is asked too. The annex has no spaces on the days those cases use. A slow-vendor case needs no upper time bound on a loaded machine: an app with no timeout returns the full answer late, and the body differs.

**What cannot be auto-graded.** Open-ended design discussion, such as caching vendor data and for how long, a circuit breaker, adding a third vendor, or how the API would change under load, goes in `solutions/explanation.md`, under `### Design`.

**Data-driven problems** come in P10, in the same theme, with the domain, database and migration tool chosen at authoring: for example, splitting a member's plan into its own table, carrying existing members forward, and refusing bookings beyond capacity under parallel requests. A SQLite problem needs Docker too, because every service project does.

## Later: learner-built systems

[ADR 0020](../decisions/0020-catalog-labels.md) names `scope: system` for problems where you build several services. They are **not designed here**: this spec has one `run`, one health path and one `port_env`. The compose network makes them possible, and the design waits ([ADR 0019](../decisions/0019-service-projects.md#later-learner-built-systems)).
