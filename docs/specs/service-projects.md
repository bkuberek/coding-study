# Spec: Service projects

**Status: built through P9, P10's backing services and P11's engine work: the sandbox, the lifecycle commands, the mock server, the HTTP grader and `cstudy dev`, so a service project works from `cstudy start` to `cstudy submit`, on macOS with Docker Desktop and [on Linux](#on-linux) with Docker Engine, and the first catalog problem, [coworking availability](#the-first-problem), uses them in TypeScript and in Python. [Backing services](#backing-services) such as Postgres and Redis run beside your app, with migrations, `grade_setup` and `reset`, and the grader can [reach a declared service](#grader-reach), which a [multi-step case](#multi-step-cases) names by its origin, through a mock server's [pass-through](#pass-through) or directly. [Code intelligence](#language-servers) runs in a sidecar for TypeScript and Python, and the [Web UI](#web-ui) runs tests, submits and holds a dev stack (P9). What is still planned says so where it stands: your own IDE's generated files and `cstudy dev`'s other flags, contract tables and the D7 check of parallel cases (P10's grader side), and the AI catalog problems that use the [extensions](#extensions) (P11). The mock server streams server-sent events, matches on request bodies and fills in run-time values, and a case can judge what a request's JSON body carried, so a [mock LLM provider](#a-mock-llm-provider) is config data.** A service project is a [project problem](problem-format.md#project-problems) where you build a small running service: `cstudy` runs your app in a Docker sandbox, with mock servers for third-party APIs and, where the problem declares them, backing services, and judges it by what it answers over HTTP. Decision record: [ADR 0019](../decisions/0019-service-projects.md), which tags each decision by who made it. Items marked R*n* there are recommendations confirmed when their phase starts. Phases P*n* are the ADR's. Existing problems, the bank projects included, stay native, need no Docker and do not change.

## Names

A service project is `kind: project` with `project.grading: http`. The name is new in the repository; `cache-service` and `notification-service` are catalog slugs and do not collide.

| Term | Meaning | Note |
|------|---------|------|
| Mock server | The Python server cstudy runs for a third-party API | Always "mock server": [`cstudy mock`](cli.md#cstudy-mock) and attempt mode `mock` are the timed practice session |
| Stack | One Docker Compose project that cstudy started, owned by one command | `dev`, `test` or `graded` |
| App container | A container of the problem's toolchain image, with your project folder mounted | The long-running one for `run`, and one-off ones for the other commands |

## Sandbox

Service projects always run in Docker, as their sandbox (owner, O15). Per-project dependencies mean running third-party code and install scripts, and security catalog starters contain deliberate flaws, so an unfixed SSRF starter could otherwise reach your LAN or a cloud metadata endpoint. Docker gives a boundary at the project folder: nothing above it is visible. The [P1 spike](../decisions/0019-service-projects.md#the-p1-spike) measured this section on macOS with Docker Desktop, and [On Linux](#on-linux) says what is measured on Linux and what stays unproven.

It runs on your own Docker, which you use for other things. cstudy never changes, requires changing, or recommends changing an engine setting; its limits are per container, on its own stacks only; and it never stops the engine (owner, O16).

### What a stack holds

cstudy generates the compose file, `.cs/runs/<run>/stack.yaml`, and merges the problem's own [backing services](#backing-services) with it.

| Container | Image | Sees | Networks |
|-----------|-------|------|----------|
| `app` | The problem's toolchain image, `project.image` | Your project folder, and the data volume at `/data` | `sandbox` |
| `cstudy-mocks` | A pinned Python image | cstudy's mock server code and the [rendered configs](#mock-server), both read-only | `sandbox`, with each mock server's name as an alias |
| `cstudy-forward` | The same pinned Python image | cstudy's forwarder code, read-only | `sandbox` and `edge` |
| Backing services | The problem's, by digest | Their own named volumes, and read-only copies of the problem's files they mount | `sandbox` |

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
| `sandbox` (`internal: true`) | Everything in the stack | None: `bootstrap`, `run`, `test`, `reset` and `grade_setup` cannot reach the internet, your LAN, a metadata address or your machine. DNS is no way out either, as measured on Engine 29: the engine's name server answers an outside name with `SERVFAIL` in under 0.2 ms, where an ordinary bridge takes about 30 ms to ask upstream, and `host.docker.internal` resolves to nothing and the addresses behind it are unreachable, so D11 probes addresses alone. Its bridge holds no address (`com.docker.network.bridge.inhibit_ipv4`): an internal network's bridge otherwise holds its gateway address, and on Linux a container reaches every service listening on all of your machine's addresses through it, `sshd` among them. It sets `enable_ipv6: false` too, since an engine set to give new networks IPv6 would give that bridge an IPv6 address, which `inhibit_ipv4` does not take away, and D11 reads `/proc/net/if_inet6` in a container on `sandbox`: only `::1` and `fe80::/10` may be there, and a missing file counts as none. Its containers still reach each other |
| `edge` (an ordinary bridge) | `cstudy-forward` only | Holds no user code |
| An ordinary bridge, `egress` | `install` containers (and `cstudy dev --exec --network`, planned) only, with no mock server or service attached | Yes, and P1 measured that it reaches your LAN and this machine's loopback services too |

**The catch.** A service only on an `internal: true` network publishes nothing, and `docker compose port` prints `:0` and exits 0 (measured), which `cstudy` treats as a failure. So the forwarder above, a small TCP relay, joins both networks. It publishes on `127.0.0.1` with a dynamic host port, read back with `docker compose port`:

| Published | When | Why |
|-----------|------|-----|
| Your app's port | Every stack | The grader, your browser and `curl` |
| The mock control port | Every stack, token-protected | The grader and the Web UI only. It is the one exception to "only the app's port is published". A grader inside the network, the alternative in R24, would remove it |
| Each port in `project.grader_reach` | Test and graded stacks only | The grader, for a service it must speak to itself, such as an identity provider's login ([Grader reach](#grader-reach)) |
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
| An engine whose default gives new networks IPv6 | `sandbox` sets `enable_ipv6: false` outright and the probe measures a user network with IPv6 on, but the tests run on an engine with IPv6 off, which is yours to set: a `sandbox` made under the other default is not exercised |
| Setuid bits | Your code can set them on files that show as yours on your machine, so `cstudy` takes them off every regular file in the project folder before and after a stack: no link is followed, a file nobody can read or a folder nobody can enter hides none, and such a folder gets its mode back |
| Limits | `mem_limit` and `pids_limit`, per container: app 512m and 256 pids, a helper 64m and 32, an install 1g and 512. A problem may declare `app.mem_limit` |
| Stopping | `init: true` and a 2 s grace, or each `down` costs 10 s with Node as PID 1 |
| Logs | `json-file` with `max-size: 10m` and `max-file: 3`, per container, so a chatty app cannot fill your disk through the engine's logs: an app that printed 50 MiB kept 24 MiB (measured). `cstudy` changes no engine setting for this |
| Environment | [Explicit only](#environment). Nothing from your machine leaks in, especially real API keys |

A problem-owned service keeps its own user and writable paths, since an engine such as Postgres needs them, and gets the rest: `cap_drop: [ALL]`, `no-new-privileges`, its limits, the capped logs, cstudy's labels and `sandbox` alone. Its root filesystem is read-only unless the problem says `read_only: false`. Each exception is per image, in [Backing services](#hardening-per-image).

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
| Installed, no permission (Linux) | The engine refuses the socket | A message of its own, by [where you stand with the docker group](#the-docker-group), that says the group is effectively root |
| Installed, stopped | `docker` exists, the engine does not answer | Started, where cstudy may start it |
| Running, no compose v2 | `docker compose version` fails | The install message |
| Running | Both answer | Nothing to do |

**When cstudy starts the engine.** Only at the moment it is needed: when you start or run a service project (`cstudy start`, `test`, `submit`, `dev`, and the Web UI's equivalents), and from `cstudy doctor --fix`. Never from `cstudy list`, `cstudy show`, the Problems or Problem view, or plain `cstudy doctor`, because starting Docker's VM costs real memory on your machine. It prints `starting Docker ...` as an `output` event, shows progress, waits up to 120 s for the engine, then reports clearly if it did not come up.

| Platform | Mechanism (starting from fully quit is not measured) | When the engine still does not answer |
|----------|------------------------------------------|----------------------------------------|
| macOS | Docker Desktop's `docker desktop start --detach`, then `open -a Docker` | `Docker did not start. Start it yourself, then run the command again.` |
| Linux, rootless Docker | `systemctl --user start docker`, which needs no root | `Docker did not start. It runs as your own user and needs no root: run systemctl --user start docker, then run the command again.` |
| Linux, system engine with `docker.socket` listening | `docker desktop start --detach`, then `systemctl --user start docker-desktop`. The socket starts the engine on the first connection, so the `docker info` that found it stopped has already tried | `Docker did not start. Its socket is listening, so connecting starts the engine, and the engine did not come up: systemctl status docker says why. Once that is fixed, run the command again, which starts it.` |
| Linux, system engine otherwise | `docker desktop start --detach`, then `systemctl --user start docker-desktop`. Starting a system service needs root, and cstudy never runs `sudo` | `Docker is not running. It is a system service, and starting a system service needs root; cstudy never runs sudo. Run sudo systemctl start docker, then run the command again.` |
| Linux, Docker Desktop or any other address | `docker desktop start --detach`, then `systemctl --user start docker-desktop` | As on macOS |

cstudy prints the message and exits 4. It tells the setups apart (`adapters/docker_setup.py`) without `sudo` and without changing anything, only once the engine does not answer:

| Setup | How it is found |
|-------|-----------------|
| Rootless Docker | The client's address, from `docker context inspect`, which `DOCKER_HOST` and the current context set, is `docker.sock` in `$XDG_RUNTIME_DIR` or in `/run/user/<uid>` |
| System engine | The address is `unix:///var/run/docker.sock` or `unix:///run/docker.sock`. `systemctl is-active docker.socket` printing `active` means the socket is listening |
| Anything else | Any other address, or a context that cannot be read |

cstudy never stops the engine, since other work may be using it. It only stops its own labeled stacks.

#### The docker group

When the engine refuses you, cstudy reads the group database and this process's groups, and the message says what to do:

| Where you stand | Message |
|-----------------|---------|
| Not in the group, or no `docker` group | `Docker refuses this user. Join the docker group: sudo usermod -aG docker $USER, then log in again.` |
| In the group database, as a member or by your primary group, and not in this process's groups | `Docker refuses this session: you are in the docker group, but this session does not have it yet. Log out and back in, or run newgrp docker in this terminal, then run the command again.` |
| In this process's groups | `Docker refuses this user, though this session is in the docker group: the socket's own permissions refuse it. docker context ls names the socket, and ls -l on it shows who may use it.` |

Each ends with `Being in the docker group is effectively root; cstudy cannot reduce that, and never mounts the socket into a container.`

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
| Backing services | The problem's compose file | S21 refuses an image without a digest. Pulled at start with the others |

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
| `grade_setup` | Graded runs and `cstudy verify` only: after every backing service's healthcheck passes and before `bootstrap`. A graded run with it first runs `bootstrap` from empty data on a stack of its own ([Graded run](#graded-run)) | A short-lived container of the same image, with the project folder and `{problem}/grading/` read-only, gone before `app` starts | Environment, plus `CSTUDY_PROBLEM_DIR` and `CSTUDY_GRADED_LEVEL` | Within the startup budget | `sandbox` | A content error, exit 4, whose output is never shown as a hidden case |

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
cstudy dev [<slug|file>] [--scenario <mock>=<scenario>]... [--events]
```

| Flag | Effect |
|------|--------|
| `--scenario` | Sets a mock server's visible scenario at start. A hidden or unknown name exits 3 with the visible names, before anything starts |
| `--events` | The stack as JSON events, and each line of standard input a scenario to switch to while it runs, for the Web UI ([the dev stack from the page](#the-dev-stack-from-the-page)) |

It runs in the foreground: it brings the stack up, prints your app's published URL and the mock server names, then what your app prints. Ctrl-C, or SIGTERM, brings the stack down and keeps its data, exit 0, and a second Ctrl-C during that cannot leave half a stack. Your app ending brings the stack down too, exit 2, and so does an app that never starts, with its output. One dev stack runs per project: a second `cstudy dev` exits 3 and names the holder's process id. The lock is `.cs/projects/<slug>.dev.lock`.

Planned:

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
  grader_reach: [idp:8080]      # a service the grader speaks to itself, test and graded stacks only
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
| `services` | A compose file, relative to the problem's directory ([Backing services](#backing-services)), held to S21 and S22 |
| `grader_reach` | At most 4 `<name>:<port>`, each a service of that file or a mock server on 8080, that the grader may reach ([Grader reach](#grader-reach)) |
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
| Static check | S15 refuses a `.env` in any starter |
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
| Matching | Method exact, and path exact except that a `{name}` segment matches any one non-empty segment, whose value is not kept. A repeated query key matches on any of its values. A route's `match` narrows it by the request's body ([below](#matching-on-bodies)). Routes are tried in the order the config lists them, and the first match wins. No state beyond sequence counters |
| Unmatched | A clear 404 that names the mock server: `{"error": "no route", "mock": "room-vendor", "method": "GET", "path": "/v1/other"}`, and a log entry with `matched: false` |
| Scenarios | The default is no scenario. A scenario overrides the matched response; a field it leaves out comes from the route, and a field it gives replaces the route's whole, `headers` included. So a 429 keeps the route's body unless it says `body: ""`. It never applies to an unmatched request |
| Responses | A mapping or list gets `Content-Type: application/json` unless the headers name one. `Content-Length` is computed unless the headers name one, so a config can lie about it on purpose. 204, 304 and `HEAD` send no body. No `Date` or `Server` header is added |
| Visibility | A scenario is hidden unless `visible: true`, so a forgotten flag cannot leak one. A dev or test stack loads only visible ones |
| `sequence` | One entry per request, in order; the last entry repeats. It stands alone: an entry carries its own fields, `delay_ms` included. Setting a scenario restarts its counter, and a request it does not apply to does not advance it |
| Reset | Sequence counters and the log reset between cases |
| Determinism | Bodies are fixed, with no randomness and no clock. A [run-time value](#run-time-values) depends only on the request it answers and that request's number since the last reset |
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

Built at P11 (R33). They let a config mock a streaming API, an LLM provider among them, with no second program: matching on request bodies, run-time values in a response, server-sent event streams that a scenario can drop, stall or break, and log assertions on what a request's JSON body carried. The code is in `adapters/mock_server/` (`json_values.py`, `templates.py`, `matching.py`, `http_server.py`) and, for the grader, `domain/http_bodies.py` and `domain/http_grading.py`.

#### Matching on bodies

Built at P11 (R33). A route can match on what the request's body holds, beside its method, path and query, so one path answers a streaming request and a plain one differently, or an embeddings request by its text.

```yaml
routes:
  - id: chat-stream
    method: POST
    path: /v1/chat/completions
    match: {body: {stream: true}}         # a JSON subset of the request's body
    response: {status: 200, body: {note: streamed}}
  - id: embed-refunds
    method: POST
    path: /v1/embeddings
    match: {body_contains: refund}        # a text anywhere in the body
    response: {status: 200, body: {data: [{embedding: [0.9, 0.1]}]}}
  - id: chat                              # no match: any other body
    method: POST
    path: /v1/chat/completions
    response: {status: 200, body: {note: whole}}
```

| Rule | Detail |
|------|--------|
| `match.body` | A JSON subset. Each field it lists must be in the body, at any depth; a list must have as many elements as the body's, each holding its own; anything else must be equal, where `true` is not `1` and `1` is `1.0`. A body that is not JSON, or is empty, never matches |
| `match.body_contains` | A text the body's bytes must hold anywhere |
| Both | A route that gives both needs both |
| Order | Deterministic: routes are tried in the order listed and the first match wins, so a route that matches on its body comes before one on the same path that does not. A request no route matches gets the usual 404 |

#### Run-time values

Built at P11 (R33). A response can carry values of the request it answers, such as the `model` it asked for or a count derived from its messages, through one small template syntax: field references and three functions, with no expressions and no scripting.

```yaml
response:
  status: 200
  body:
    id: "chat-{{seq}}"                                  # text around a value: a string
    model: "{{request.body.model}}"                     # a value alone: its own JSON type
    usage: {prompt_tokens: "{{words(request.body.messages)}}"}   # a number
```

| Rule | Detail |
|------|--------|
| References | `{{request.method}}`, `{{request.path}}`, `{{request.body}}` and `{{request.body.<dotted path>}}`, where a number names a list element, as in `messages.0.content`; `{{request.query.<name>}}`, its first value; `{{request.headers.<name>}}`, the name in any case; and `{{seq}}`, the request's number at its mock server since the last reset, as the [log](#request-log) counts it |
| Functions | `len(<reference>)`: a text's characters, a list's elements or an object's fields, else 0. `words(<reference>)`: the whitespace-separated words of every text in the value, at any depth, keys not counted, else 0, a deterministic stand-in for a token count. `json(<reference>)`: the value's compact JSON text, `null` when it is missing |
| Where | Every string of a `body`, a mapping's or list's or a text, the text of a `body_file`, and a [streamed](#streaming) event's `data` and `raw`, in a route's response or a scenario's. Not in headers, and not on a [pass-through](#pass-through)'s answer |
| In a JSON body | A string that is one value and nothing else takes that value with its own JSON type, a missing field as `null`, so `"{{len(request.body.messages)}}"` sends a number. Any other string is filled in as text. Keys are never filled in |
| In a text | A string goes in as it is, anything else as its compact JSON, and a missing field as nothing. A text that holds JSON names a string with `json(...)`, which quotes and escapes it |
| Missing | A field the body lacks, or a body that is not JSON, is missing, never an error: a mock server answers what it can |
| Anything else | Anything else in braces is sent as written, and S20 refuses a `{{` that opens no value, since that is a typo far more often than it is meant. So a mock cannot send a literal `{{` |
| No clock | No value reads the clock or a random source, so a case can compare a filled-in body exactly |

#### Streaming

Built at P11 (R33). A response can be a stream of server-sent events, `text/event-stream`, in place of a body, with a wait before each event, and a scenario can cut it short or break it.

```yaml
routes:
  - id: chat-stream
    method: POST
    path: /v1/chat/completions
    match: {body: {stream: true}}
    response:
      status: 200
      stream:
        - {data: '{"delta": "Desk "}', after_ms: 20}
        - {event: usage, data: '{"tokens": {{words(request.body.messages)}}}'}
        - {data: "[DONE]"}
scenarios:
  dropped_mid_stream:
    visible: true
    route: chat-stream
    drop_after_chunks: 1             # one event, then the connection closes, with no [DONE]
  stalled:
    route: chat-stream
    stall_after_chunks: 1            # one event, then silence until the app gives up
  malformed_event:
    route: chat-stream
    stream:
      - {data: '{"delta": "Des'}     # JSON cut short
      - {raw: "dta: no such field\n\n"}   # a frame sent as written
```

| Rule | Detail |
|------|--------|
| `stream` | A list of events in place of `body` or `body_file`. Each is `data`, sent as one `data:` line per line of it, under an optional `event` name, or `raw`, text sent as written, for a frame that breaks the format. `after_ms` waits before the event, after the headers for the first. [Run-time values](#run-time-values) fill in `data` and `raw` |
| The answer | `Content-Type: text/event-stream` unless the headers name one, and no `Content-Length`: like every answer it is HTTP/1.0, so closing the connection ends the stream. `HEAD`, 204 and 304 send no events |
| `drop_after_chunks` | In a scenario or a sequence entry: sends that many events, then closes the connection cleanly, with no terminator. An HTTP/1.0 answer ends at its close either way, so the app learns of the drop by the end event that never came, `[DONE]` or whatever its API names |
| `stall_after_chunks` | Sends that many events, then nothing, and holds the connection open until the app closes it, or for 10 s, the program's bound on a client that stopped reading. A stall tests the app's own timeout; a case whose app has none times out |
| A malformed event | A scenario's own `stream`, with `data` that is not JSON, or a `raw` frame |
| Overrides | A body and a stream are one field. A scenario's `stream` replaces the route's body or stream, and its `body` replaces a route's stream: a 429 that gives `body` answers with that body and no events, while one that gives only `status` and `headers` keeps the route's stream. `drop_after_chunks` and `stall_after_chunks` are ignored on an answer with no stream, so one scenario can apply to every route |
| Waits | A stream's `after_ms` add up to at most 3 s (S20), and count with `delay_ms` toward a case's [hang guard](runners.md#hang-guard-and-restarts) |
| Log | An entry's `responded_ms` is set when the stream ends: after its last event, its drop, or its stall. The log's [bounds](#request-log) are unchanged |

#### Logged bodies

Built at P11 (R33). A case's [`log`](#hidden-http-case) entry can judge what a request's JSON body carried: that a gateway capped `max_tokens`, that its fallback sent the second provider the same messages as the first, or that a conversation's history only grew, which is what a provider's prompt cache needs.

```json
"log": [
  {"mock": "primary", "route": "chat-stream", "count": 1,
   "body": {"stream": true}, "body_max": {"max_tokens": 256}},
  {"mock": "backup", "route": "chat-stream", "count": 1,
   "body_same_as": {"mock": "primary", "route": "chat-stream", "fields": ["messages"]}},
  {"mock": "primary", "route": "chat", "count": 2, "body_prefix_stable": "messages"}
]
```

| Field | Rule |
|-------|------|
| `body` | Only requests whose JSON body holds this subset count, by the rules of a mock server's [`match.body`](#matching-on-bodies). Its strings may name [captures](#multi-step-cases). A body that is not JSON holds nothing |
| `body_max` | Only requests whose body holds a number at most this at each dotted path count, such as `{"max_tokens": 256}`. A missing field, a string or a boolean there does not count. A path names a list element by its number, as in `messages.0.content` |
| `body_same_as` | Only requests whose body holds, at each of `fields`, the same value as the first request `mock` logged on `route`, or its first request at all without a `route`, count. Values compare as JSON, whatever their key order, so `1` is not `1.0`. If that mock server logged no such request, or its body lacks a field, the assertion fails, saying so. Its mock server and route must exist (S23) |
| `body_prefix_stable` | A dotted path. The requests that count, in the order they came, each hold there a text or a list that starts with the whole of the previous one's: a text by its characters, a list by its first elements, each the same JSON. A request that lacks the field, or holds anything else there, fails it. It is an assertion alone, so `count` is optional beside it; with fewer than two requests it holds |
| With the others | These narrow what counts together with `route`, `headers` and `form`, then `count`, `min_count`, `max_count`, `min_gap_ms` and `body_prefix_stable` judge what is left. A failure names what narrowed: `backup chat-stream with body messages the same as primary chat-stream: expected 1 request, saw 0` |
| Limits | The [log's](#request-log) bounds are unchanged. A body cut at its 64 KiB fails any of these with `a logged body was cut at the log's limit, so its JSON cannot be judged`, and a log that overflowed fails them as it fails `form` |

**The byte-prefix check, read simply.** R33 asked for a byte-prefix check across requests, and the first sketch said each request's whole body bytes start with the previous request's whole body. A JSON body closes its brackets after its last message, so a growing conversation never does that, and a provider caches the prompt it reads from the JSON, not the body's bytes. So the check reads one field, the one that grows: a text by its characters, which are its bytes once encoded, and a list element by element, each compared as canonical JSON text. A system prompt that gains a timestamp, a history rewritten in place, or tools reordered between calls break it; another key order or spacing does not. A second `log` entry checks a second field, such as `system` or `tools`.

#### A mock LLM provider

Built at P11 (R33). A mock LLM provider is config data on this format, with no key and no cost, served by the same program as every other mock server. An example ships as `cli/tests/fixtures/mock_configs/llm-provider.yaml`: a generic chat-completions-style API, named after no vendor, which the mock server's tests serve on loopback and an end-to-end test grades a gateway through.

```yaml
shape_version: "generic chat-completions style, public docs of 2026-11"
routes:
  - id: chat-stream
    method: POST
    path: /v1/chat/completions
    match: {body: {stream: true}}
    response:
      status: 200
      stream:
        - data: '{"id": "chat-{{seq}}", "model": {{json(request.body.model)}}, "choices": [{"index": 0, "delta": {"role": "assistant", "content": "Oak "}}]}'
          after_ms: 20
        - data: '{"id": "chat-{{seq}}", "choices": [{"index": 0, "delta": {"content": "is free."}, "finish_reason": "stop"}]}'
          after_ms: 20
        - data: '{"id": "chat-{{seq}}", "choices": [], "usage": {"prompt_tokens": {{words(request.body.messages)}}, "completion_tokens": 3}}'
        - data: "[DONE]"
  # chat: the same path without stream, a whole answer with usage
  # embed-refund and embed: /v1/embeddings, a vector chosen by match.body_contains
scenarios:
  rate_limited:
    visible: true
    status: 429
    headers: {Retry-After: "1"}
    body: {error: {type: rate_limit, message: "Too many requests: retry after 1 s."}}
  # rate_limited_then_ok, dropped_mid_stream, stalled_stream, malformed_chunk, overloaded
```

| Rule | Detail |
|------|--------|
| What the example covers | A streamed chat answer that ends in `[DONE]` with a last event of token usage; the same path answered whole when `stream` is not true; an embeddings endpoint whose vector is chosen by the text it embeds; a 429 with `Retry-After`, alone and before the stream; a stream dropped after one event, one stalled after one event, one with a malformed chunk; and a 503. Its model is echoed from the request, and `prompt_tokens` counts the words of the messages, roles included, a deterministic stand-in for a tokenizer. There is no `total_tokens`, since run-time values do no arithmetic |
| A fake key | The problem's `project.env` gives the app a fake key, such as `LLM_API_KEY: cs-fake-llm-key`, which reaches no provider, since nothing in a stack can. A `log` entry asserts the app sent it: `{"mock": "llm", "route": "chat-stream", "count": 1, "headers": {"Authorization": "Bearer cs-fake-llm-key"}}` |
| A problem owns its config | A problem copies the example into its own `mocks/`, edits it to the shape its statement and its `mocks/<name>.API.md` document, and owns it from then on. Nothing keeps a copy in step with the example |
| Shape drift | Provider response shapes drift, so a config modeling a real API records `shape_version`: which shape it copies and from when. It is a record for authors, which the schema allows and a stack's rendering leaves out; no check can tell drift, and cstudy never compares a config with a live API |
| Out of scope | Per-request token signing for a mock identity provider. Use a service container, decided at the first identity problem (R34) |

### Pass-through

Built at P11. A mock server can stand in front of a [backing service](#backing-services), such as an identity provider, and pass its requests through. Each request is logged as a route's is, so a case can count the app's calls to the provider and read what they carried, and a scenario can spoil a token on its way back. The mock server never signs anything: the provider signs, and a scenario only breaks what it signed (R34).

```yaml
upstream: http://keycloak:8080        # a service on the stack's network: http://<name>:<port>
routes:
  - id: token
    method: POST
    path: /realms/pp3/protocol/openid-connect/token   # no response: passed through
  - id: certs
    method: GET
    path: /realms/pp3/protocol/openid-connect/certs
scenarios:
  alg_none:
    route: token
    jwt: {field: id_token, tamper: alg_none}
  bad_signature:
    route: token
    jwt: {field: id_token, tamper: bad_signature}
  token_outage:
    visible: true
    route: token
    status: 503                       # answers alone: the provider is not called
```

Here the mock server's name, say `idp`, is the name the app and the grader use, and `keycloak` is the service's own name, which only the mock server needs.

| Rule | Detail |
|------|--------|
| `upstream` | One per mock server, `http://<name>:<port>` with no path, where `<name>` is a service of the problem's compose file (S20). A route without `response` passes through to it, and so does a request no route matches, which is logged with `route: null` and `matched: false` instead of the 404. Without `upstream`, every route needs its `response` |
| The request | Goes out as it came: method, path, query, headers and body, the `Host` included, so the provider hears the name the app used. Headers about one connection (RFC 9110, 7.6.1) are dropped, and `Accept-Encoding` becomes `identity`, so a JWT in the answer can be read |
| The answer | Comes back whole, with every `Set-Cookie` line apart, and the mock server writes its own `Content-Length`. An upstream that does not answer within 10 s, or answers more than 8 MiB, is a 502 whose JSON names the mock server and the upstream |
| Scenarios | On a pass-through route, a scenario entry with a `status` answers alone and calls no upstream, so an outage on a token route spends no code at the provider. Any other entry overrides the upstream's answer field by field, as it would a route's own response: `headers` replaces all of them, `body` the body, `delay_ms` delays it |
| `jwt` | In a scenario or a sequence entry only. `field` is a dotted path to the token in the JSON answer, passed through or the route's own. `alg_none` gives the token the header `{"alg":"none"}` and an empty signature, and keeps its payload, so the per-login `nonce`, `aud` and `exp` stay right and only the algorithm is wrong. `bad_signature` changes the first character of the signature. Neither needs a key. A body with no JWT at that field goes out unchanged, so the reference fails the case in `verify`, which shows the mistake |
| Log | An entry of a pass-through has `status: null` until the upstream answers. Bodies and headers are kept within the [log's limits](#request-log) |
| Visibility | Unchanged: a `jwt` scenario is hidden unless `visible: true`, and a dev or test stack never holds a hidden one |

The mock server and every [backing service](#backing-services) join `sandbox`, so the mock server reaches its upstream there. To let the grader drive a login through it, the problem lists the mock server in [`grader_reach`](#grader-reach), `idp:8080` here, and a case names it as `http://idp:8080`. A test on a real engine grades that chain whole: a case reaches a stand-in service through the mock server with the original `Host`, the request log counts the call, and the output check reads what the app printed.

## Backing services

Built at P10, and measured on macOS with Docker Desktop (Engine 29.9.2, arm64) by the tests on a real engine and the fixture `5903-fixture-members-python` ([A small example](#a-small-example)).

Docker is how service projects get backing services such as Postgres, Redis and AWS services emulated locally. A problem with none still runs in Docker, and a problem may keep SQLite in `CSTUDY_DATA_DIR`.

The compose file belongs to the problem, so you cannot edit what grading trusts, and it is tool-neutral, so any image can be used. It holds only services and their volumes. cstudy merges it into the stack's own file, `.cs/runs/<stack>/stack.yaml`, and adds what the table below says. The fixture's:

```yaml
services:
  db:
    image: postgres:17.11-alpine@sha256:3540c0362c809df084ffac0ae69fe794515f9de92692f02178bcdce0ef0302ac
    user: postgres
    environment: {POSTGRES_USER: app, POSTGRES_PASSWORD: app, POSTGRES_DB: app}
    volumes: [pgdata:/var/lib/postgresql/data]
    tmpfs: [/var/run/postgresql:mode=1777, /tmp:mode=1777]
    mem_limit: 256m
    pids_limit: 128
    healthcheck:
      test: [CMD, pg_isready, -U, app, -d, app, -h, 127.0.0.1]
      interval: 30s
      start_period: 120s
      start_interval: 250ms
volumes:
  pgdata:
```

Your code reads `DATABASE_URL`, `REDIS_URL`, `AWS_ENDPOINT_URL` or whatever the problem names, from `project.env`, reaching the service at its stable name such as `db:5432`. A service publishes no port. To look inside it, use `docker compose exec` on the printed project name.

### What cstudy adds

| Item | Rule |
|------|------|
| Network | `sandbox` alone: no egress, and nothing published but what [`grader_reach`](#grader-reach) names, through the forwarder, in a test or graded stack |
| Capabilities and privileges | `cap_drop: [ALL]` and `no-new-privileges`. S21 refuses `cap_add`, `cap_drop`, `security_opt` and `privileged`, so a problem cannot change them |
| Root filesystem | Read-only, unless the service says `read_only: false`; an image's exception is [per image](#hardening-per-image) |
| Labels and logs | The stack's container labels, and the same log caps as cstudy's own containers |
| Limits | The service's own `mem_limit` and `pids_limit`, both required by S21 |
| Ready | Every command of the app's image, `grade_setup` and `bootstrap` among them, and the app itself, waits for each service's healthcheck. All of it runs on the [first clock](#two-clocks), so a case's time starts at ready, as before |
| Volumes | Each of the file's volumes carries the stack's labels. A test or graded stack's go with its `down -v` and with the sweep; a dev stack's stay, and [`cstudy start --fresh`](#cleanup) removes them |
| Files | A bind mount names a file or folder beside the compose file. cstudy copies it under `.cs/runs/<stack>/services/`, refusing a link on the way or inside, makes the copy readable by the service's own user and mounts it read-only |
| Images | Pulled at problem start with the others, then `--pull never` |
| A file nobody verified | A stack holds the file to S21 before it starts, and only the fields a backing service may set reach the stack, so a problem of your own that never ran `cstudy verify` cannot run what S21 refuses |

A service may set `image`, `command`, `entrypoint`, `environment`, `healthcheck`, `mem_limit`, `pids_limit`, `volumes`, `tmpfs`, `user`, `working_dir`, `read_only`, `depends_on` (the file's own services only), `stop_grace_period`, `stop_signal`, `shm_size` and `init`, and nothing else ([S21](#static)). Mount a named volume on each path the image declares as a `VOLUME`: otherwise Docker makes an anonymous one, which carries no label, and a dev stack's `down` leaves it.

### Hardening per image

What each image needs beyond the defaults above, as measured. A service that runs as the image's own user does so because the official entrypoints step down from root through `gosu`, which needs capabilities a backing service never holds.

| Image | Runs as | Exception | Measured |
|-------|---------|-----------|----------|
| `postgres:17.11-alpine` | `user: postgres` | Read-only root with tmpfs on `/var/run/postgresql` and `/tmp`; data on a named volume at `/var/lib/postgresql/data`, which the image's user owns | 117 MB download on amd64, 115 MB on arm64. 38 MiB in use under the fixture's cases, limit 256m, 128 pids |
| `redis:7.4.12-alpine` | `user: redis` | None: data on a named volume at `/data` | 17 MB download. 9 MiB in use, limit 64m, 32 pids. Redis 7.4 and later are source-available (RSALv2 or SSPLv1), not open source, which allows this use; Valkey, the BSD-licensed fork, fits a problem that wants an open license |
| `motoserver/moto:5.2.5` | `user: "65534:65534"` | Read-only root with tmpfs on `/tmp`; it runs as root by default and needs none of it | [AWS services](#aws-services-moto) |
| `quay.io/keycloak/keycloak:26.8.2` | The image's own, 1000 | `read_only: false` without a build cache, since its first start writes into `lib/quarkus`; read-only with a build-cache volume mounted read-only | From its spike, not run by cstudy yet: [Keycloak](#keycloak) |

A whole test stack with Postgres and Redis, `bootstrap` and `reset`'s `prepare` was ready in 4.3 s, and a graded one, with `grade_setup` too, in 5.0 s, both on the first clock. The app took 23 MiB and the forwarder 21 MiB beside them.

### AWS services: Moto

AWS services come from Moto server, which needs no account. P10 measured `motoserver/moto:5.2.5` (2026-10-27), pinned `@sha256:59a1965d845249b04def37a0e2565f9cc6c44543cb89b68e90f28f344b3b0d1a`, the multi-architecture index. Its license is Apache-2.0, as the package's metadata states. It ran on an internal network built as `sandbox` is, hardened as a backing service is, and boto3 in a second container reached it through the SDK's endpoint override (`endpoint_url=http://moto:5000`, region `us-east-1`, fake keys):

| Service | What worked |
|---------|-------------|
| S3 | Create a bucket, put an object, get it back, list the bucket |
| SQS | Create a queue, send, receive with a wait, delete; the queue was empty after |
| DynamoDB | Create a table on demand, put and get an item, and a conditional put refused with `ConditionalCheckFailedException` |
| No egress | Neither a public address nor the metadata address, and no outside name resolved, from that network |

| Measured | Value |
|----------|-------|
| Download | 102 MB on amd64 and on arm64; 564 MB unpacked |
| Pull | 11.0 s here |
| Start to ready | 1.76 s as root at 256m, 0.82 s as nobody at 128m |
| Memory | 46 to 48 MiB idle, 75 to 77 MiB at its peak under the three services |
| Recommended | `user: "65534:65534"`, `mem_limit: 128m`, `pids_limit: 32`, tmpfs on `/tmp` |

**Verdict:** Moto serves S3, SQS and DynamoDB offline, so no problem needs the fallback for them. For a service Moto cannot serve well, a problem may use `localstack/localstack:4.14.0`, the last LocalStack image that runs without an account, pinned by digest; it is not built or measured. The current LocalStack images stop at start without an auth token, which would need an account and internet access from the sandbox, so no problem uses them. A healthcheck needs no extra tool, since the image holds Python:

```yaml
  aws:
    image: motoserver/moto:5.2.5@sha256:59a1965d845249b04def37a0e2565f9cc6c44543cb89b68e90f28f344b3b0d1a
    user: "65534:65534"
    tmpfs: [/tmp]
    mem_limit: 128m
    pids_limit: 32
    healthcheck:
      test: [CMD, python, -c, "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/moto-api/data.json', timeout=1)"]
```

### Keycloak

Not a fixture: its image is 265 MB and a stack takes 13.6 to 26.5 s to start, too much for tests that run on every change to the sandbox. A problem plugs it in as any service, with what the Keycloak spike measured (26.8.2):

- `image: quay.io/keycloak/keycloak:26.8.2@sha256:3879c623248408de29a5303178b5816c77e8dfef3890c361f8c0bbeaa979ba3b`, `command: [start, --http-enabled=true, --hostname=http://idp:8080, --import-realm, --cache=local, --health-enabled=true]`, `read_only: false`, `mem_limit: 512m`, `pids_limit: 128`.
- The realm, a JSON file beside the compose file, bind-mounted at `/opt/keycloak/data/import/`; cstudy mounts its copy read-only.
- A healthcheck with bash alone, since the image holds no `curl`, that asks for the realm's discovery document on the main port: `exec 3<>/dev/tcp/127.0.0.1/8080 && printf 'GET /realms/<realm>/.well-known/openid-configuration HTTP/1.0\r\nHost: idp:8080\r\n\r\n' >&3 && timeout 2 grep -q '"issuer"' <&3`. Keycloak serves that document only once the realm import is done. Do not check `/health/ready` on the management port 9000: its body says `"UP"` in a sub-check a few seconds before the import ends, while every request still answers 503, so a problem that trusts it starts the grader too early. Give `start_period` room (`0280` uses 180 s) since the first start builds the server.
- `grader_reach: [idp:8080]`, so the grader drives the login form itself with `Host: idp:8080`, and `--hostname` keeps every URL Keycloak emits the same for the app and the grader.

The build cache that makes it read-only and 13 s faster, a named volume filled once by `kc.sh build`, is not built.

**Known limit: a stateless service needs a small `bootstrap`.** S19 and S23 assume that a backing service holds data: S19 requires a `bootstrap` beside `services`, and S23 requires `commands.reset` for a case that asks for `fresh` with data. Keycloak holds its realm in an embedded database and imports it at each start, so it has nothing to migrate and nothing to reset. A problem on Keycloak declares a small `bootstrap` anyway, `0280` only checks in one that the provider answers with the issuer the app will use, and it has no `fresh` case and no `reset`. The rules stay as they are; this is recorded so a later problem on a stateless service does not take the requirement for a mistake.

### Grader reach

The contract between the stack and the grader's multi-step cases (P11). Some services must be reached by the grader itself, such as an identity provider whose login form the grader fills in as a browser would.

| Part | Rule |
|------|------|
| Manifest | `project.grader_reach`: at most 4 `<name>:<port>`, each a service of the compose file or a mock server on 8080 (S19). None of the stack's own containers: the grader reaches your app at `app_url` |
| Stack | In a test or graded stack, the forwarder listens on a port of its own for each, from 10000 and clear of the app's, and publishes it on `127.0.0.1` with a dynamic host port, read back with `docker compose port`. A dev stack publishes none |
| Grader | `StackEndpoints.origins` (`application/http_grading_ports.py`) maps each entry's origin, `idp:8080` as `http://idp:8080`, to `http://127.0.0.1:<port>`, and a case names it so ([Reaching an origin](#reaching-an-origin)). A client dials that URL and sends `idp:8080` as `Host`. The app's own origin, `http://app:<app.port>`, is `app_url`, and an origin in neither is refused, by S23 before a run and by the grader during one |
| Host | The forwarder relays bytes, so the service sees the `Host` the client sent, measured with a service that echoes it. Any protocol passes, HTTP or not |

### Known limits

Engine gaps found while building `0283` to `0287`. None blocks a problem; each is worked around in the problem that met it.

- **Backing services cannot be stopped or paused by a case.** No case can stop or pause a service, and the mock server's pass-through only proxies HTTP, so a problem cannot grade "the store went down" by taking the store away.
- **A kept restart needs a no-op reset.** With services, S23 requires `commands.reset` for any `fresh` case. Restarting the app while keeping its data therefore needs a `reset` that does nothing, as `0284` declares.
- **Parallel cases judge status counts only.** They never compare bodies.
- **The `unordered` comparator applies to every step of a multi-step case.**
- **Moto holds a whole S3 object in memory.** A large object needs a bigger memory limit on the Moto service and a disk-backed `/tmp` for it.
- **Moto allows `PurgeQueue` once every 60 s.**

Left by R33's [extensions](#extensions), each with its way around:

- **Your app's streamed answer is judged as its whole text.** The grader reads an answer to its end and compares `expected.body` as an exact string; it parses no events, so a problem fixes its event format byte for byte, as the end-to-end test's gateway does. Only the first body byte is timed, by [`first_byte_ms_max`](#hidden-http-case); the gaps between later events are not.
- **Run-time values do no arithmetic and fill in no header.** A `total_tokens` is left to the app, and a header that should echo the request is fixed text.
- **A mock cannot send a literal `{{`.** S20 refuses one that opens no run-time value.
- **A stall holds its connection for at most 10 s.** An app whose own timeout is longer meets the stream's end there, with no terminator.

Found while building `0289` to `0292`:

- **A mock cannot compute a vector per element of a batched embeddings request.** Run-time values fill in text, not one embedding per input, so a mock embeddings API is a table of exact batches matched with `match.body`, as `0291` does.
- **A log assertion's label shows only the first 40 characters of its expected body.** A long `body` subset is cut in the reason, so the case's `note` says what was expected.
- **A case cannot combine `steps` with `before`.** Setup requests become the first steps.

**Valkey is the open store used.** `valkey/valkey:9.1.3-alpine`, the BSD-licensed fork of Redis that speaks its protocol, backs `0285` in place of Redis, so a Redis client reaches it unchanged and the problem carries no source-available license.

## Databases

Built at P10, and [parallel cases](#parallel-cases) after it, except their D7. [Contract tables](#contract-tables) are not built.

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

Migration tools track what they applied, so hidden data cannot simply be inserted before anything has run. `grade_setup` therefore applies only the problem's baseline migrations, using the problem's own tool, and inserts hidden data; `bootstrap` then applies the remainder, because the tool's tracking table already records the baseline. The specifics stay inside the designer's script, so the core stays tool-neutral. The core's part of this flow is proven by the fixture `5903-fixture-members-python`, whose tool is a small runner that records each migration with its checksum: `grade_setup` applies its own copy of the baseline, records it as the runner would, and loads member 900; `bootstrap` applies the rest; and a migration that recreates the table passes every visible case and loses that member, which a hidden case catches. The catalog problem `0282-inventory-reservations-typescript` proves it with a real tool, node-pg-migrate 9.0.0: its `grade_setup` runs node-pg-migrate's own `runner` on the problem's copy of the baseline with `count: 1`, which records it in `pgmigrations`, then loads the hidden products; `bootstrap` runs `node-pg-migrate up`, which finds the baseline recorded and applies the rest; and a level 4 migration that drops the stock column without copying it loses the hidden products' stock, which a hidden case catches. Proving it with Liquibase or Alembic is left to the first problem that picks one ([migration tools](#authoring-guidance-migration-tools)). `CSTUDY_GRADED_LEVEL` lets the script load only the data of the graded levels. Hidden rows use identifiers from a range the statement reserves, so your seed rows cannot collide with them. If you edit a baseline migration, the tool's own checksum report is what you see.

The script and its files never enter the `app` container. The rows it loads do reach the database your app reads, which is inherent in this design.

### Contract tables

A design point. For live-read checks, where the service must see a change made behind its back, a problem may declare tables as a stable contract that the grader writes to mid-run and that you may not rename:

```yaml
project:
  contract_tables: [member_credits]
```

A case then names a problem-owned script as `write_data`, run as `grade_setup` is. **A contract table limits your schema freedom**, so the statement names it, and a problem uses one only when neither the API nor a mock server can make the change.

### Reset

Data resets per run. A problem that needs a reset between cases declares `commands.reset`, and a case asks for it with `fresh: true`. cstudy stops the app, runs `reset` with `CSTUDY_RESET_PHASE=apply`, and starts the app again. `CSTUDY_RESET_PHASE=prepare` runs once after `bootstrap`. PostgreSQL's `CREATE DATABASE ... TEMPLATE` is an example of such a command, not a core feature: the fixture's `prepare` copies the migrated database to a template, and its `apply` drops the database `WITH (FORCE)`, creates it again from the template and empties Redis with `FLUSHALL`. On Postgres 17.11 with the fixture's tables, the copy took 31 ms and putting it back 87 ms (69 to drop, 18 to create). Without `commands.reset`, `fresh: true` only restarts the app.

### Parallel cases

Built after P10 and P11 (R11), in the grader's code: `ParallelBurst` in `domain/http_case.py`, the count in `domain/http_parallel.py`, the sending in `application/http_grading_parallel.py`, and `HttpAppClient.send_together` in `adapters/http_grader/clients.py`. Its D7 and the summary line are planned. A case type for N requests against limited capacity. It gives language-neutral concurrency grading, which is what SQLite cannot show, since a row lock and a lost update need a database that serves writers at once.

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

| Field | Rule |
|-------|------|
| `parallel` | `count`, 2 to 64 as for stress workers, and a `request` shaped as a single request's, sent to your app, or `requests`, 2 to 8 of them that the burst takes in turn: request `i` is `requests[i % length]`, which is how two orders take the same rows in opposite orders. Each string has `{i}` replaced by the request's index, from 0, in the path, query values, header values and `json` strings |
| `expected_statuses` | How many answers come back with each status, or class such as `"4xx"`; a status counts toward itself before its class. The counts add up to `count` (S23). The verdict counts statuses, never their order |
| `after` | Optional: one request with its `expected`, sent once every answer is in, to judge the state they left. It is sent even when the counts are wrong, since that state explains them |
| `before` | Optional, as a single request's: sent in order first, each must answer 2xx |
| `repeat` | 1 to 10, default 1: the whole case runs again after each run that passed, each from a reset, so it needs `fresh` (S23). The first run that fails is the verdict and names itself: `run 2 of 3: ...` |
| Sending | A thread and a connection per request, held at a barrier until every thread is ready, so no request waits for another to be sent |
| Limit | The case's limit covers `before`, the burst and `after`. The burst spends what its slowest request took, since they run side by side, and a request with no whole answer ends the case as a single request's would |
| Report | `actual` holds how many answered each status, `{"statuses": {"201": 5, "409": 15}}`, and the `after` answer, and `expected` the same shape, so a visible case's example reads that way too. A failure gives both counts in full: `20 requests at once: expected 5 to answer 201 and 15 to answer 409; 8 answered 201 and 12 answered 409` |

`mocks`, `log`, `comparator` and `app_output` work as for a single request, judged after the last answer. A pass finds no race and proves none: planned, the summary adds a line as for stress cases ([cli](cli.md#cstudy-submit)), and a problem with parallel cases has at least one broken overlay that they catch (D7). Until D7 is built, a problem names the check-then-update solution its parallel cases fail under `### Pitfalls and edge cases`. Measured on loopback with a stand-in app that waits 50 ms between reading a stock and writing it back: 10 requests behind the barrier oversold on every run, and the same app holding a lock passed every run. On a real stack, `0282-inventory-reservations-typescript` with a solution that reads what is available and then inserts its hold, with no lock, failed each of its six stock races on the first run (`20 requests at once: expected 3 to answer 201 and 17 to answer 409; 9 answered 201 and 11 answered 409`), and one that locks rows in the order its items came failed both deadlock cases with 500s.

## HTTP grading

One piece of core code covers every language, with no per-language runner work. No runner job is involved. Existing entry-class problems keep their path. The grader runs on your machine, outside every container, and reaches your app and the control interface through the forwarder's published ports, so hidden cases never enter a container.

### The code

Step 6 of the [graded run](#graded-run), as a use case that is handed a ready stack: `run_http_grading` in `application/http_grading.py`, with `domain/http_case.py`, `domain/http_grading.py`, `domain/http_steps.py`, `domain/http_parallel.py` and `adapters/http_grader/`; `application/http_grading_steps.py` sends a case's steps and `application/http_grading_parallel.py` a parallel case's burst. It returns a `Judgement`, so levels, submissions and events are today's. `application/service_grading.py` brings its stack up and `application/graded_stack.py` adapts that stack.

The grader asks a stack for little, through `GradedStack` in `application/http_grading_ports.py`:

| Member | What it is |
|--------|------------|
| `endpoints` | `app_url` and `control_url` on `127.0.0.1`, `control_token`, and the names in `mocks`. `control_url` is `None` without mock servers |
| `restart_app()` | Stops your app and starts it again, for a case that hung it |
| `restart_app_with_fresh_data()` | For `fresh`: stops your app, runs `commands.reset` with `CSTUDY_RESET_PHASE=apply` if declared, starts your app |
| `app_exit(within_ms)` | Your app's exit code and stderr tail, or `None` if it still runs after waiting that long, since a container's exit shows a moment after its connections drop |
| `app_output(since_s)` | What your app printed, standard output and error together, since a moment in seconds since the epoch, for an [output check](#output-check). One `docker compose logs --since` call, through `SandboxEngine.app_output_since`; a read that fails is a stack failure, not a verdict |

Both restarts return once the health path answers again, and raise `StackStepError` otherwise.

### Two clocks

Every time limit and hang guard starts only once the stack is ready (owner, O17). Starting it, and each restart above, runs on the first clock and counts toward no case. Its budget is generous, 300 s for `up --wait` unless `project.timeouts_s.startup` says otherwise and `app.ready_timeout_s`, 60 s by default, for the health path after that, and running out of it says so with its own message and changes no result.

A case's limit runs from its first request to the last byte of its last answer, `before` requests included. It holds for the whole exchange, so an app that sends a byte now and then cannot outlast it. The limit on `commands.test` starts at ready as well, and the times `cstudy test` and `cstudy submit` report leave startup out, showing it apart as `not counted`.

### Graded run

`cstudy submit`, and D1 and D3 of `cstudy verify`:

1. Check `requires` and the install record; pull images and install if needed.
2. Render the configs, with every scenario, and generate the compose file.
3. With `grade_setup`, the from-empty check: a stack of its own, under a fresh name, brings up the mock and service containers and runs `bootstrap` on empty data, with the app idle, then goes with its data (`down -v`). A failure is a [migration failure](#failure-reporting) that says it was from empty, and it shows its output even in a mock attempt, since no hidden data is there. Without `grade_setup`, the `bootstrap` of the next step is itself this check.
4. Bring up a fresh stack (`up --wait`), with its one-shots in order before `app`: `grade_setup` if declared, `bootstrap` if declared, `reset` with `prepare` if declared. The app's start depends on them and on the mock container being healthy, which P1 measured faster than separate steps, with one failure path.
5. `app` runs `commands.run`. Poll the health path through the published port until 2xx or `ready_timeout_s`, each try limited to 5 s as a whole, so an answer that never ends still counts as no answer. The second clock starts here.
6. For each case of the graded levels, in `tests.json` order: `POST /reset`; if `fresh`, restart with fresh data and `POST /reset` again, so your app's startup meets no scenario left by the last case and the log holds this case's requests alone; set scenarios, send `before` requests and the request, or the `steps`, compare, assert on the log, then run any [cleanup](#multi-step-cases) steps.
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
| `request` | `method`, `path`, optional `query`, `headers`, and one of `json`, `body` and `body_base64`. A `query` value is a string, or a list sent once per value. `json` is encoded and sends `Content-Type: application/json` unless `headers` name one. `body` goes out byte for byte, so it can be malformed. `body_base64` is a binary body, such as a file upload, in standard padded base64: the grader decodes it and sends the bytes raw, with no `Content-Type` unless `headers` name one: `{"method": "PUT", "path": "/files/a.png", "headers": {"Content-Type": "image/png"}, "body_base64": "iVBORw0KGgo="}`. The schema refuses two of these together |
| `expected.status` | Required: a status, or a class of them such as `"4xx"`, which holds every status of its hundred |
| `expected.body` | Optional; left out, any body passes. A string is the body's exact text. Anything else is compared parsed, by `comparator`, so key order and whitespace cannot fail a correct answer, and `null` asks for a JSON null. An object must hold exactly the fields expected: an extra one fails and is named. `NaN` and `Infinity` are not JSON |
| `expected.headers` | Optional. Each listed header must match, its name in any case. A `Content-Type` that names no parameter ignores the answer's, so a framework's `; charset=utf-8` cannot fail it |
| `expected.first_byte_ms_max` | Optional: the most milliseconds from writing the request to the first byte of the body the grader reads, or to the end of an empty body; headers alone do not count. It tells a stream from an answer held back until it is whole, which brings the same bytes in the same total time: `{"status": 200, "first_byte_ms_max": 1000}`. Past it, the reason says when the byte came, in whole milliseconds rounded up: `first body byte after 2140 ms, expected within 1000 ms`. A wrong status says only that. With redirects followed, it times the last request. It must be under the case's hang guard, or the case would time out first (S23). Keep it generous: a first event a mock server sends after 50 ms and a stream that ends after 2 s leave room for a busy machine on both sides |
| `comparator` | Overrides the problem's: `{"type": ...}`, with `tolerance` for `float`. `exact`, `unordered`, `unordered-nested` or `float` ([Comparators](problem-format.md#comparators)). `checker` is not allowed |
| `log` | Assertions per mock server and route: `count`, `min_count`, `max_count`, and `min_gap_ms`, measured from each response's `responded_ms` to the next request's `received_ms`. Without `route`, they cover every request the mock server logged, matched or not, and requests past the log's limit still count. A log that overflowed fails an assertion with a `route` or a `min_gap_ms`, saying so: `dropped` says how many came and not which route they took or when, and the retry too soon may be the very one it did not keep. A value a little below the wait, here 950 for 1 s, tolerates timers. `headers` and `form` narrow what counts to the requests that carried each header, by its name in any case, or each field of a form-encoded body, such as `{"form": {"refresh_token": "{{rt2}}"}}` with `count: 1`. Their values may name [captures](#multi-step-cases). A log that overflowed fails them too, and so does a body cut at the log's 64 KiB, whose form cannot be read. `body`, `body_max`, `body_same_as` and `body_prefix_stable` judge a JSON body ([Logged bodies](#logged-bodies)) |
| `fresh` | Restart the app and run `commands.reset` first |
| `app_output` | What your app may not print while the case runs: `{"absent": [...]}` ([Output check](#output-check)) |

A case has a `level`, or no graded run would reach it. `project.clock: virtual` is refused with `grading: http`: these cases run on the real clock. The bound on waits and D11 keep them stable.

A case that names a mock server the stack lacks, or a scenario a mock server lacks, or a problem whose comparator is `checker` or `ops` with no override, is a content error rather than a verdict. S23 catches these first.

### Multi-step cases

Built at P11 (R34). A case has either `request` or `steps`. The grader acts as a browser: a later step can carry values captured from earlier answers, cookies stay in named jars, and a step can follow redirects. That is what a login, a CSRF form or an OIDC flow needs, with no browser and nothing specific to one provider. Cases stay data: one template syntax, and no scripting.

```json
{"version": 1,
 "flows": {
   "login": [
     {"request": {"method": "GET", "path": "/login"},
      "expected": {"status": 302},
      "capture": {"auth": "header.location"}},
     {"request": {"method": "GET", "url": "{{auth}}"},
      "expected": {"status": 200},
      "capture": {"form": "form.kc-form-login.action"}},
     {"request": {"method": "POST", "url": "{{form}}",
                  "form": {"username": "{{user}}", "password": "learner-pass"}},
      "expected": {"status": 302},
      "capture": {"callback": "header.location", "code": "header.location.query.code"}}]},
 "cases": [
   {"id": "h3", "level": 2, "note": "a callback with a forged state is refused",
    "steps": [
      {"use": "login", "with": {"user": "learner"}},
      {"request": {"method": "GET", "path": "/callback",
                   "query": {"code": "{{code}}", "state": "forged"}},
       "expected": {"status": "4xx"}},
      {"request": {"method": "GET", "path": "/me"}, "expected": {"status": 401}}],
    "cleanup": [{"request": {"method": "POST", "path": "/logout"}}],
    "log": [{"mock": "idp", "route": "token", "count": 0}]}]}
```

| Rule | Detail |
|------|--------|
| `steps` | In place of `request`, `expected` and `before`; at least one request. A step is a `request` with an optional `expected` and `capture`, a `use` of a flow, or a step that sends nothing: a [sleep](#steps-that-send-nothing). A case passes when every step does. The first step that fails ends the case, and the reason names it: `step 2 GET /callback: expected a 4xx status, got 302`. When every step was taken, the last request's answer is judged together with `log`, as a single request's is, even when steps that send nothing follow it |
| `request` | As a single request's, plus: `url` in place of `path`, `form`, `jar` and `follow_redirects`. `form` is sent as `application/x-www-form-urlencoded` unless `headers` name a `Content-Type`; one of `json`, `form`, `body` and `body_base64` at most. A `body_base64` names no capture |
| `path` and `url` | A `path` goes to your app, as every single request does. A `url` is `http://<name>:<port>/<path>`, an origin as the stack's network names it, or a capture that holds one. The grader dials the address the stack publishes for that origin and sends its name as `Host`, so the app and a provider see the same names a container would. The origins a case may name are your app's own, `http://app:<app.port>`, and each entry of [`grader_reach`](#grader-reach), a backing service or a mock server, such as `http://idp:8080` ([below](#reaching-an-origin)). `https` is not sent: nothing in a stack has a certificate |
| `expected` | A single request's fields, with a status class such as `"4xx"`, and the case's comparator. Left out, any answer passes, which a step that only captures or a cleanup step may want. `first_byte_ms_max` times each step on its own, from writing that step's request, and a late byte names the step: `step 2 POST /v1/chat: first body byte after 2140 ms, expected within 1000 ms`. A parallel case's `after` request takes it too |
| `capture` | A name per value read from the answer: `status`; `header.<name>`; `header.<name>.query.<parameter>`, a query parameter of a header that holds a URL, such as `Location`; `body.<dotted path>`, where a number names a list element and a value that is not a string is kept as its JSON text; `form.<id>.<attribute>`, an attribute of the HTML `<form>` with that `id`; `input.<name>.<attribute>`, of the `<input>` with that `name`. HTML entities are unescaped, as a browser would. A value missing from a right answer fails the step and names where it looked. A wrong answer captures nothing |
| `{{name}}` | The one template syntax. It fills a captured value in as it is, in a later step's `path`, `url`, `query` values, `headers` values, `json` strings, `form` values, `body`, and `expected` header values and body strings, and in `log` `headers` and `form` values. A name is letters, digits and `_`. No expression, filter or escape: anything else in braces is sent as written, and S23 refuses a `{{` that opens no name. `{i}` stays the parallel case's index, and `{problem}` the command placeholder |
| Cookies | Each case starts with no cookies. A step's request uses the jar `main` unless `jar` names another, which is another browser: a second login, or a callback that arrives with no login cookie. A jar sends and keeps cookies as a browser would, by origin and path, with `Expires` and `Secure` honored, so `/login` and `http://app:8000/callback` share your app's. A single-request case keeps no cookies, as before |
| Redirects | Not followed unless `follow_redirects: true`, so a flow can capture each `Location`. A followed 301, 302 or 303 becomes a GET with no body and none of the step's headers; a 307 or 308 repeats the request. Up to 10 hops, within the case's limit. A redirect to an origin the stack does not publish is not followed: it is the step's answer |
| `flows` | Named step lists at the top of tests.json, such as `login`, written once and used by any case with `{"use": "login"}`. `with` fills each `{{name}}` of the flow's steps with its text, which may name a capture itself; a name it leaves out is a capture. A flow may use another flow, not itself. Captures in a flow are the case's, as if its steps were written in place: a flow's step is named `step 1, login step 3` |
| `cleanup` | Steps after the case whatever happened, even after a failure or a timeout, to undo what it changed in a provider: a mapper, a key, a lifespan. They get the case's limit afresh, and each runs whatever the others did. One that names a value no step captured is passed over, since what it would undo never happened. One that fails, or gets no answer, fails a case that passed, with the step named, since later cases would meet what it left. No cleanup runs once your app has exited or hung too often |
| Limits | The case's limit covers every step, sleeps included, as it covers `before` requests |
| Verdict | `fail`, `timeout`, `error` and `invalid` as for a single request, from the step where it happened. A step that cannot be sent, for a URL no stack publishes, fails the case with the step named |

Provider state persists across the cases of a run, since restarting a service such as Keycloak per case would cost seconds. A case that changes it undoes the change in `cleanup`.

S23 checks a multi-step case before any run: each `{{name}}` is captured by an earlier step, or by a step at all for a cleanup step and `log`; each `{{` opens a name; each `url` written out names a declared origin, your app's or a `grader_reach` entry's, while a `url` that is itself a capture is checked when it is sent; each step's `first_byte_ms_max` is under the case's hang guard. A step that uses a flow tests.json lacks, or a flow that uses itself, fails loading, naming the case and the step.

#### Steps that send nothing

Built after P11. A multi-step case can wait between two requests, or after the last one before its `log` is read, for an app that should act on its own meanwhile: a retry in the background, a cache entry that expires.

```json
{"id": "h7", "level": 2, "note": "the cached price expires after 1 s",
 "steps": [
   {"request": {"method": "GET", "path": "/prices/oak"}, "expected": {"status": 200}},
   {"sleep_ms": 1200},
   {"request": {"method": "GET", "path": "/prices/oak"}, "expected": {"status": 200}}],
 "log": [{"mock": "price-vendor", "route": "price", "count": 2}]}
```

| Rule | Detail |
|------|--------|
| `sleep_ms` | 1 to 10,000 ms. It counts toward the case's limit as a request does, so the next request has that much less left. One that outlasts what is left ends the case as `timeout`, as an answer that came too late would. Its label reads `step 2 sleep 1200 ms` |
| S23 | The sleeps of a case add up to less than its hang guard, or the case would time out first |
| Where | In a case's `steps` only: not in a flow, a cleanup step or a parallel case |

A sleep replaces the slow mock route some problems wait with; those problems keep theirs.

#### Output check

Built at P11. A case, single-request or multi-step, can forbid what your app prints, for a problem that teaches you to keep secrets out of logs:

```json
"app_output": {"absent": ["{{code}}", {"regex": "eyJ[A-Za-z0-9_-]+\\.eyJ[A-Za-z0-9_-]+\\."}]}
```

| Rule | Detail |
|------|--------|
| What is read | Your app's standard output and error together, from the moment the case began, before any fresh start, to the end of its cleanup, as the engine stamped each line. A line printed after the last answer of one case may fall into the next case's window, which an absent check tolerates |
| `absent` | Each item is a text, which may name a `{{capture}}`, or `{"regex": ...}` in Python's syntax, searched anywhere. A text that names a value no step captured is passed over, since what was never captured cannot have been printed |
| Verdict | Each match fails a case that was judged, `pass` or `fail`, and the reason shows the start of what was printed and the rule it broke: `app output: printed "eyJhbGciOiJSUzI1NiJ9.eyJ…", which matches eyJ…`. A case that timed out or errored reads no output |
| S23 | Each pattern compiles, and each `{{name}}` is captured by a step |

#### Reaching an origin

Built: this is where P10's [grader reach](#grader-reach) and P11's cases meet, with one notion of what a case can reach. The grader asks the stack for one thing per origin, through `StackEndpoints` in `application/http_grading_ports.py`:

| Field | What it is |
|-------|------------|
| `app_origin` | Your app's origin inside the stack, `http://app:<app.port>`. `SandboxGradedStack` sets it; the grader reaches it at `app_url` |
| `origins` | For each `grader_reach` entry, by its origin inside the stack, `http://idp:8080`, where the grader reaches it on your machine, `http://127.0.0.1:<port>`, through the forwarder. `SandboxGradedStack` fills it in a test or graded stack |

`grader_reach` is the one list: a mock server that stands in front of a provider, `idp` in the [pass-through](#pass-through) example, is reachable when it is listed there, as a backing service is, and not otherwise. `address_of(origin)` reads the two fields, and a test fakes them with any mapping. S23 accepts the origins `declared_origins` in `domain/http_origins.py` returns, your app's and each `grader_reach` entry's, so a case passes the static check exactly when a stack publishes what it names.

### What you see

`--json` and `--events` keep version 1 of the [event stream](cli.md#event-stream), with additive changes only, so the CLI and the Web UI render it:

`cstudy test --json` on a service project prints one document: `slug`, `language`, `attempt_id`, `outcome` (`passed`, `failed`, or `load_failed` when your code kept the stack from becoming ready), `exit_code`, `levels`, `load_error`, `tests` (`commands.test`, as its `test_result`; empty without a ready stack), `cases` (the visible cases, each with its `level`), `tally` (of those cases), `startup_s` (the first clock) and `duration_s` (the second). Progress and the lines of `commands.test` go to standard error. The exit codes are those of the report.

| Event | On a service project |
|-------|----------------------|
| `output` | Progress: Docker start, image pull, install, the stack's start, its readiness and its end, each with `stack`, its stage (`docker`, `pulling`, `installing`, `starting`, `ready`, `failed`, `stopped`), and `startup_s` on `ready`; and every line `commands.test` prints |
| `test_start`, `test_result` | `cstudy test --events`. One result for `commands.test`, with id `commands.test` and origin `starter`: `pass` on exit 0, `fail` with `message` (`exited with 1`) and the last 4 KiB of its output as `stdout`, or `timeout` past its limit. Its output streams through `output` before the result, since cstudy does not parse a framework |
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

Measured for PP5 on 2026-11-09, from the registry's manifests: `liquibase/liquibase:4.33.0` is a 453 MB download on arm64 and 457 MB on amd64, with Java and no Node, and `eclipse-temurin:21-jre-noble` alone is 98 to 100 MB, beside 81 MB for `node:24-slim`. A TypeScript problem's app image must hold Node and a JRE, no official image holds both, and a problem cannot build an image (S19), so PP5 does not use Liquibase. In short: Liquibase weighs about 455 MB with no Node, and `node:24-slim` has no Java runtime, so a TypeScript problem uses a Node migration tool. Liquibase fits a JVM problem, whose image holds Java already, or a separate one-off container.

**node-pg-migrate**, which PP5 uses: a common migration tool for Postgres on Node, pinned at 9.0.0 with `pg` 8.23.1, pure JavaScript, so the install needs no build and no script. It applies plain SQL files in name order, each in a transaction of its own, records each by name in `pgmigrations`, reads `DATABASE_URL`, and refuses to run when a recorded migration is missing or out of order. It keeps no checksum, so an edited baseline goes unnoticed. Its `runner({count: 1})` applies only the first file, which is how `grade_setup` applies the baseline with the tool itself. A script outside the project loads it from the project's `node_modules` with `createRequire`, since the working directory is the project folder.

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
| [Problems view](web-ui.md#problems-view) | `needs docker`, or `needs docker postgres`, after the title, from `requires` alone. A filter of the same values is planned |
| [Problem view](web-ui.md#problem-view) and its Start dialog | The full list, with each requirement's state, from `GET /api/v1/problems/{slug}/needs`. A requirement not met here keeps Start from starting and shows the CLI's words |

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

`cstudy start` and the Web UI's Start show the summary before any download begins. The Web UI's Start downloads nothing: the first run or `cstudy dev` pulls and installs, with its progress, so the page asks for no confirmation. They ask for confirmation only when something will be downloaded or a requirement is missing. `cstudy start --yes` skips the prompt for scripts; without a terminal and without `--yes`, a start that would download exits 3 and names the flag. If a requirement is missing, Start says what to install rather than failing midway, exiting 4 before it writes anything, as a JDK outside the range does. A stopped Docker engine is not missing: Start starts it ([Docker states](#docker-states)).

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
| Backing services | Each declares its own limit, which counts toward the stack's. Postgres held 38 MiB under a 256m limit, Redis 9 MiB under 64m and Moto 75 MiB under 128m; Keycloak needs at least 320 MiB, and 512m is its limit ([Hardening per image](#hardening-per-image)) |
| Disk per project | `node_modules` or `.venv`: 27 MB for the TypeScript problem, measured at P7, and 9 MB for the Python one, measured at P8; plus images and the install cache, shared across projects |
| Container output in memory | What a container prints is as long as it likes, and `cstudy dev` follows an app with no time limit. So `cstudy` holds the last MiB of a command's output, each line goes by as it comes, and a line with no newline comes in pieces of 64 KiB |
| Docker | [Resources and CI](#resources-and-ci) |
| Language servers | None until P9; then each project counts toward `cstudy serve`'s limit of four language servers |

### Cleanup

There is no `cstudy reset` and no command that removes a problem; verified against `entrypoints/commands/`.

| Action | What it removes |
|--------|-----------------|
| `cstudy start --fresh`, or a review attempt | `archive_folder` runs `remove_untracked` first, so `node_modules`, a real `.venv`, and caches are deleted, not archived. The next start installs again. The dev stack's data goes too, its own volume and each backing service's, so the next `cstudy dev` migrates from empty; a running `cstudy dev` keeps it, and the start says so |
| Deleting `projects/<slug>/` by hand | Everything in it. A resumed attempt copies the starter and installs again |
| `.cs/build/projects/<slug>/` | The reference's copy and its install, recreated by `cstudy verify` |
| `cstudy doctor --fix` | Docker leftovers, by label only |
| `cstudy dev --reset-data` | The dev volume |
| Images | Never removed by cstudy, since other work may use them |

## Code intelligence and editors

**The riskiest part of the design.** The spike measured that it works, close to the host's speed. The language servers are built (P9, 2026-11-10); your own IDE's files are planned.

### Language servers

Built in P9 (R28). Sandboxed code writes a service project's folder, so no server on your machine reads it: basedpyright or tsserver there would run what the folder names. A code-intelligence session on a TypeScript or Python service project runs its server in a sidecar of its own instead, and talks to it through `docker exec`, exactly as the broker talks to a server on your machine ([Code intelligence sessions](web-ui.md#code-intelligence-sessions)).

| Item | Rule |
|------|------|
| The sidecar | One per session: a compose project of its own, `cstudy-l-<pid of cstudy serve>-<id>`, so it needs no mock server or backing service and does not wait for the dev stack. One `lsp` service, named after the stack, idling on `sleep infinity` with `init` |
| Image | `node:24-slim` pinned by digest, the same for both languages: the servers in `.cs/lsp/` are Node programs, and a TypeScript project's own image is this one. A session never pulls it, and never starts Docker |
| Isolation | `network_mode: none`, the app's hardening (read-only root, `cap_drop: ALL`, `no-new-privileges`, your UID and GID, a 64 MiB `/tmp`), 768 MiB of memory and 128 processes. The project folder and `.cs/lsp/` are mounted read-only, each at the path the session names it by, from the path with its links resolved, so the server's URIs are the page's |
| Servers | The workspace's own `.cs/lsp/`, the same files and versions as on your machine (typescript-language-server 6.0.3, basedpyright 1.40.2): the install does not grow. TypeScript runs the project's own compiler, `<project>/node_modules/typescript/lib`, so the workspace's `typescript/` is not needed; basedpyright reads the project's `[tool.pyright]`, whose `venv = ".venv"` the template writes, and finds the `.venv`'s packages without Python, which the image does not have |
| Session | `docker exec --interactive --workdir <project> <sidecar> node <.cs/lsp>/<script> --stdio`, with the Docker client's environment and none of the variables that hide directories: nothing hidden is mounted, and no variable crosses `docker exec`. `initialize` names no `processId`, since the sidecar cannot see `cstudy serve` and the servers would exit at once; they stop at the end of their input instead |
| Start | Once the page's CSRF message arrives: Docker's state and the image are asked first, then `docker compose up --detach`, about 0.3 s, then the server |
| Stop | With the session: the server's stop sequence, then `docker compose down` and the run's folder. A guard takes the sidecar down if `cstudy serve` dies, and the sweep knows the stack by its name and owner |
| Docker not usable | The socket closes with 4004 and a calm reason: `Docker is not running`, `Docker is not installed`, `Docker has no compose v2`, `Docker refuses this user`, or `needs the node image: docker pull <node:24-slim@sha256:…>` for a Python project whose `cstudy start` did not pull it. The status bar shows the reason with Restart, in its usual colour ([Status bar](web-ui.md#status-bar)) |
| Other languages | A service project in a language whose server runs in no sidecar yet keeps `no_code_intelligence`: `service_project` ([`cstudy status --json`](cli.md#cstudy-status)); the page shows `code intelligence for <Language> service projects comes later` and a session is refused with 422 `usage`, `no code intelligence for go service projects yet` |

Measured on the catalog's first service projects, on macOS with Docker Desktop: TypeScript's first diagnostics 1.4 s after `didOpen` (1.6 s after the server started), 366 MiB in the sidecar, 386 MiB at peak; basedpyright's 0.8 s, 129 MiB, 140 MiB at peak. The spike measured TypeScript at 504 MiB at peak on an Express project, which the 768 MiB limit holds.

A language server must not read a mock config or a hidden case, and inside the container there is nothing to hide: none of them are mounted. ADR 0018's four [hidden directories](web-ui.md#hidden-directories), `.cs/build/`, `.cs/cases/`, `.cs/runs/` and the content root, do not exist there.

| Item | Where it is | Covered by |
|------|-------------|------------|
| Mock configs, compose files, `grading/`, `tests.json` | The problem's files | Not mounted in `app`, nor in the sidecar |
| A graded run's generated files and rendered configs | `.cs/runs/<run>/` | Not mounted in `app`, nor in the sidecar; rendered configs in `cstudy-mocks` only |
| A reference's copy and install | `.cs/build/projects/<slug>/` | Not mounted, unless it is the folder under `cstudy verify` |

What the spike answered, and P9 kept:

- **Where the server comes from.** `.cs/lsp/` mounted read-only in the sidecar. basedpyright needs no Node in a Python image then.
- **Which container.** The sidecar, not the app's, since TypeScript alone took 468 MiB of anonymous memory.
- **Stopping it.** Killing the `docker exec` client stops both servers, because they exit on end of input.
- **Definitions outside the folder.** None in the sidecar design, for these two servers: a definition into `node_modules`, the `.venv`'s `site-packages` or typeshed in `.cs/lsp/` names a file of the bind-mounted folders, which the library tab reads on your machine at the same path ([Definitions and library files](web-ui.md#definitions-and-library-files)).

Otherwise service projects use existing roots: the session's root is the project folder, basedpyright resolves imports through the folder's `.venv`, and tsserver through its `node_modules`. Non-Node servers come with their languages' phases.

The page reads the list of languages for its attempt (`GET /api/v1/code-intelligence/languages?attempt_id=N`, [Code intelligence](web-ui.md#code-intelligence)), which judges a service project's servers as its sidecar runs them: TypeScript is installed once `.cs/lsp/` holds it, whether or not the workspace's `typescript/` has its `node_modules`.

### Your own IDE

Planned (R29).

| Item | Rule |
|------|------|
| IDEs | The user's own IDE probably uses a generated `devcontainer.json`, naming the same image, mount and network, written by `cstudy dev`. VS Code and IntelliJ read it. LazyVim does not, so the spike tries a per-project server command there |
| Debugging | `cstudy dev --debug` publishes the template's debug port on `127.0.0.1`, for Node's inspector or debugpy. Paths match because of the same-path mount |
| A host toolchain | Not needed. An editor running its own server on your machine finds `.venv` pointing at an interpreter that exists only in the container, and native packages built for Linux |

## Web UI

| Item | Phase |
|------|-------|
| Run tests and Submit from the attempt page, with `cstudy test --events` and `cstudy submit --events`, the stack's stages in the results panel, and Cancel, which takes the stack down ([Attempt view](web-ui.md#attempt-view)) | P9, built |
| A dev stack starts only on request from the attempt page, because of its memory, and stops with the page, with the same idle rule as [language servers](web-ui.md#lifecycle-and-limits) ([Dev stack](web-ui.md#dev-stack)) | P9, built |
| Stack and mock server status, and a scenario picker over the control interface, through `cstudy dev --events` | P9, built |
| `.env` is an ordinary file in the tree | P4, built |
| The dependency list in the Problems view, the Problem view and the Start dialog. The page's Start downloads nothing, so it asks no confirmation: the first run, or `cstudy dev`, pulls and installs, and the results panel shows it as the `pulling` and `installing` stages | P9, built |
| The Docker messages in Start, in the Attempt view before any run, at the end of a run that Docker stopped, and in the [Health view](web-ui.md#health-view) | P9, built |
| Code intelligence through the [container](#language-servers), in TypeScript and Python | P9, built |

If a terminal holds the dev stack, the page shows that and does not start a second.

### The dev stack from the page

`cstudy dev [<slug|file>] [--scenario <mock>=<scenario>]... --events` runs the dev stack as `cstudy dev` does and writes it as JSON events on standard output, one per line, version 1, so the [Web UI](web-ui.md#dev-stack) renders it ([`schemas/dev-events.schema.json`](../../schemas/dev-events.schema.json)):

| Event | Fields |
|-------|--------|
| `output` | A progress notice, as in the [event stream](cli.md#event-stream) of `cstudy test`, with `stack` on a stage and `startup_s` on `ready` |
| `dev_ready` | `app_url` (`http://127.0.0.1:<port>`), `startup_s`, and `mocks`: each mock server's `name`, `scenario` (null for none) and `scenarios`, its visible ones |
| `app` | `text`: a line your app printed |
| `scenario` | `mock`, `scenario` (what it holds now) and `message` (why the switch was refused, or null), once per line of standard input |
| `dev_end` | Last, whatever ended the stack: `outcome` (`stopped` on Ctrl-C or SIGTERM, exit 0; `app_exited`, exit 2; `load_failed`, exit 2, with `output`, what your app printed; `error`, with the exit code of the refusal, `error: ...` on standard error too), `exit_code` and `message` |

Each line of standard input, `{"mock": "room-vendor", "scenario": "outage"}`, switches a mock server over the [control interface](#control-interface) while the stack runs; `"scenario": null` sets none, which resets every mock server and sets the others' scenarios again. A hidden or unknown scenario or mock server, or a line that is no switch, is refused in `message` and changes nothing. The terminal's `cstudy dev` prints the stack's stages as notices too, `starting the stack`, `the stack is ready after 2.4 s, not counted` and `the stack is down`.

## Checks

### Static

| Check | Rule |
|-------|------|
| S5 (changed) | An example marks a visible case with `<!-- case: <id> -->`, in the `## Level` it belongs to |
| S14, S15, S16 (changed) | With `grading: http`: no `entry`, `tests`, `clock`, `signature` or generated-test rules, and no `ops` comparator rule. A track other than `practical` is allowed ([ADR 0020](../decisions/0020-catalog-labels.md#rule-changes)). The starter holds `README.md` and its lock file, and no `.env` or `.env.local`, since `cstudy` writes `.env` from `project.env`. S15's rules on `package.json`, `pyproject.toml` and lock files [flip](#lock-files-and-static-checks). A `request` in a case belongs to a service project |
| S19 (new) | `commands` holds only the standard names; `run` and `test` are declared, `install` with `requires.lock`, `bootstrap` with `services`; each is a non-empty list of strings; `{problem}` only in `grade_setup`, whose script lies outside the starter; `image` pinned by digest; `app` complete; `env` holds `port_env` with `app.port`; a URL in `env` names a declared mock server on 8080 or a service of the compose file; each `grader_reach` entry names a service of the compose file or a mock server on 8080, and none of the stack's own containers; at most 4 mock servers with unique names, none reserved |
| S20 (new) | Every mock config valid against `schemas/mock.schema.json`, as the problem loads; a config lies in `mocks/`; `body_file` stays inside `mocks/`, exists and is text; each `{{` in a body opens a [run-time value](#run-time-values); every scenario's `delay_ms`, `Retry-After` and stream `after_ms` in all are at most 3 s, and `Retry-After` is whole seconds; an `upstream` names a service of the compose file; `room-vendor.API.md` and its starter copy at `vendors/room-vendor/API.md` are byte-identical and list every visible scenario and no hidden one |
| S21 (new) | Nothing in the compose file reaches past the sandbox, and a stack holds the file to it before it starts. The file holds only `services`, at least one, and their `volumes`. A service sets only `image`, `command`, `entrypoint`, `environment`, `healthcheck`, `mem_limit`, `pids_limit`, `volumes`, `tmpfs`, `user`, `working_dir`, `read_only`, `depends_on`, `stop_grace_period`, `stop_signal`, `shm_size` and `init`, so `privileged`, `cap_add`, `network_mode`, `pid`, `ipc`, `devices`, `ports`, `networks`, `env_file`, `extends`, hooks, `build` and anything else are refused, including what compose adds later. Its image is pinned by digest; `mem_limit` is a size and `pids_limit` a positive number, both required; its `healthcheck` has a test and is not disabled; it waits only for the file's own services; its name is lowercase letters, digits and `-`, neither reserved nor a mock server's. A mount is a bind inside the problem, never the Docker socket, a named volume the file declares, or a tmpfs; no anonymous volume. A volume takes no settings, no `external`, driver, options, name or labels, and is not named `data` or `cache` |
| S22 (new) | `requires` agrees with the compose file, the lock file and `commands`: `services` names the images' repositories, `lock` exists and `images_mb` has a row per image. Static only: a stack does not refuse a list that disagrees |
| S23 (new) | Every HTTP case: levels numbered from 1, a level of its own, and every level with a case; `mocks` names known scenarios, visible ones only in a visible case; `log` names known routes, its `body_same_as` too; `fresh` with data needs `commands.reset`; a comparator that can judge a body; waits within the case's hang guard, and each `first_byte_ms_max` under it. In a [multi-step case](#multi-step-cases), each `{{name}}` was captured before it is used, each `{{` opens a name, and each `url` written out names your app's origin or a `grader_reach` entry's. In a [parallel case](#parallel-cases), `expected_statuses` adds up to `count`, and `repeat` comes with `fresh`; the schema holds `count` from 2 to 64 |

### Dynamic

| Check | Rule |
|-------|------|
| D1 (changed) | The starter: `install` and `bootstrap` succeed, `run` answers the health path, a graded run of level 1 reports a result for every case (cases may fail), `test` runs without crashing: it may fail, and it may not time out or fail to start |
| D3 (changed) | The reference passes every HTTP case through the [graded run](#graded-run), as the starter with its overlay |
| D9 (changed) | The reference: `commands.test` exits 0, and the visible cases pass. No generated test files exist |
| D7 (extended) | Planned; [parallel cases](#parallel-cases) are built without it: a broken overlay passes every sequential case and fails each parallel case in its `caught_by` |
| D11 (new) | `install` leaves the lock's digest unchanged; `bootstrap` succeeds from empty and twice in a row; three runs of the reference give the same verdicts; the slowest case stays within 50% of its hang guard; the install is within 25% of `requires.sizes.install_mb`; a probe on `sandbox` reaches no public, LAN or metadata address, and not your machine at the gateway of any of the stack's networks, on ports 22, 80 and 443, where a refusal counts as reaching it, and holds no IPv6 address but `::1` and `fe80::/10`. Outside NFR-3's 30 s per problem, as D6, D7 and D10 are |

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
| New | D11 passes. A data-driven problem also has a baseline, its `grade_setup` runs, and a from-empty `bootstrap` passes. A problem with parallel cases has a broken overlay caught, once D7 is built |

## A small example

`cli/tests/fixtures/service_projects/` holds three working problems for the tests on a real engine. They are no catalog problems.

| Fixture | What it uses |
|---------|--------------|
| `5901-fixture-rooms-typescript`, `5902-fixture-rooms-python` | A mock server, `bootstrap`, `reset` on a file in `CSTUDY_DATA_DIR`, levels, hidden cases with the 429 scenario, a reference and a naive solution that a hidden case catches |
| `5903-fixture-members-python` | Postgres and Redis as [backing services](#backing-services), `pg8000` (pure Python, so `--no-build` holds), a migration runner of its own, `grade_setup` with a hidden member, `reset` from a template database, and a naive migration that recreates the table and loses that member. It installs 8.5 MB, about 11 once its tests have run, and its stacks used about 91 MiB at their peak |

## On Linux

Measured on Linux Mint 22.3, kernel 7.0.0-34-generic, Docker Engine 29.8.1 with its iptables firewall and AppArmor, x86_64: by the tests on a real engine, and with the first catalog problem through `cstudy start`, `cstudy dev`, `cstudy test`, `cstudy submit` and `cstudy start --fresh`.

| Item | Measured |
|------|----------|
| `internal: true`, the forwarder, the egress probe | From the app and the mock server on `sandbox`, in a dev, a test and a graded stack: no public, LAN, VPN or metadata address, no other bridge's gateway, no outside name, no `host.docker.internal`, and, with the bridge holding no address, no service of your machine's ([Networks](#networks)). The probe finds the address of a user network made with `--ipv6` and a `fd00:c5d::/64` subnet, and `sandbox` holds none. The forwarder publishes on `127.0.0.1` only |
| Hardening | Your UID, every capability set empty with `NoNewPrivs`, AppArmor's `docker-default` profile enforced, a read-only root, and the pids limit refusing a fork past it |
| File ownership | What `install` and the app write in the project folder, a named pipe and a link included, and the data volume belong to your UID and group, never root. `cstudy submit` hashes the folder, `--fresh` archives it, and you can remove it |
| Engine advice | The system engine is found with `docker.socket` listening. A socket of mode 000 at `DOCKER_HOST` gives the message for a session in the docker group. A missing socket at `DOCKER_HOST` runs Desktop's two commands, which fail, and gives `Start it yourself`. A missing socket at `/run/user/<uid>/docker.sock` runs `systemctl --user start docker`, which fails with no such unit, and gives the rootless message |

What stays unproven on Linux:

| Item | Why |
|------|-----|
| SELinux labels, rootless Docker | Not exercised |
| `host.docker.internal` | Not defined by default on Linux, so what `install` reaches there differs |
| Setuid bits | Clearing one changes a mode without following a link, which an older glibc cannot do: the bit then stays. Not exercised |
| Starting a stopped engine | Starting rootless Docker, and the messages for a socket-activated and a system engine, are shown only by tests with a scripted Docker |
| The message for a session without the docker group | Dropping a group from a process needs root, so only tests with a scripted group database show it |

## The first problem

Original to cstudy ([ADR 0004](../decisions/0004-original-problem-wording.md)). A coworking space sells hot desks, counted per day in its own data, and meeting rooms, in time slots from outside vendors. One API serves both. It is built in TypeScript as `problems/0277-coworking-availability-typescript/` and in Python as `problems/0278-coworking-availability-python/`, each a separate problem as [ADR 0014](../decisions/0014-project-problems.md) requires, with its own starter, reference and explanation. The same `tests.json`, mock configs and seeded desks grade both: a problem reads only its own files, so each holds a copy, and `cli/tests/content/test_coworking_availability.py` keeps the copies the same.

| Level | What it asks |
|-------|--------------|
| 1 | `GET /desks` already answers the count for a day on sale. Give it the right answers to a wrong request, so the starter passes 4 of its 14 cases and `cstudy done` keeps its meaning |
| 2 | `GET /availability`: one answer with the desks and `room-vendor`'s open slots, flattened and sorted |
| 3 | Vendor failure handling: a 5xx, a 429 with and without `Retry-After`, a slow answer and a broken body. Desks are still answered and the vendor is named in `unavailable`, with retries bounded and the request log checking the count and the gaps |
| 4 | `annex-vendor`, a second mock server with another shape and its own failures, among them an error in the body of a 200. One vendor failing touches nothing of the other's |

In TypeScript the stack is `node:http` and `fetch`, with no runtime dependency, so the install is the same 27 MB as the fixtures'. In Python it is the standard library, `http.server` for the API, `urllib.request` for the vendors and a thread per vendor from `concurrent.futures`, with pytest the only dependency, so the install is the template's 9 MB. There is no database: the seeded counts are a file in the starter, so the problem declares neither `bootstrap` nor `reset`. Every level is graded again on each submit, so `/desks` stays a separate endpoint, a slot names its vendor from level 2, and `unavailable` is a list from level 2, which lets an earlier level's cases hold once the annex is asked too. The annex has no spaces on the days those cases use. A slow-vendor case needs no upper time bound on a loaded machine: an app with no timeout returns the full answer late, and the body differs.

**What cannot be auto-graded.** Open-ended design discussion, such as caching vendor data and for how long, a circuit breaker, adding a third vendor, or how the API would change under load, goes in `solutions/explanation.md`, under `### Design`.

**Data-driven problems** come after P10, which built what they need, in the same theme, with the domain, database and migration tool chosen at authoring: for example, splitting a member's plan into its own table, carrying existing members forward, and refusing bookings beyond capacity under parallel requests. A SQLite problem needs Docker too, because every service project does.

## Later: learner-built systems

[ADR 0020](../decisions/0020-catalog-labels.md) names `scope: system` for problems where you build several services. They are **not designed here**: this spec has one `run`, one health path and one `port_env`. The compose network makes them possible, and the design waits ([ADR 0019](../decisions/0019-service-projects.md#later-learner-built-systems)).
