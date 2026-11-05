# ADR 0019: Service projects run a real app in a Docker sandbox against mock servers and optional backing services, graded over HTTP

| Field | Value |
|-------|-------|
| Status | Accepted as a plan. Nothing here is built, and implementation has not started. The items under [Open to confirm](#open-to-confirm) are confirmed when their phase starts |
| Date | 2026-11-05, revised the same day by [O15](#decided-by-the-owner): service projects always run in Docker |
| Spec | [service-projects](../specs/service-projects.md) (planned). Today's behavior stays in [problem-format](../specs/problem-format.md#project-problems), [runners](../specs/runners.md#project-jobs), [authoring](../specs/authoring.md#project-problems), [cli](../specs/cli.md#cstudy-submit), [installation-and-workspaces](../specs/installation-and-workspaces.md#project-folders) and [web-ui](../specs/web-ui.md#file-api-rules), each of which carries a forward pointer until its phase lands |
| Supersedes in part | [ADR 0014](0014-project-problems.md): for service projects only, the rejection of a venv or `node_modules` per project and of test tools that need a network install. Existing problems do not change |
| Amends | [PRD](../prd.md) (NFR-6: what "works on your own machine" means, as the owner defined it; [ADR 0021](0021-ai-reviewed-problems.md) amends it too) |
| Builds on | [ADR 0001](0001-data-driven-tests.md), [ADR 0004](0004-original-problem-wording.md), [ADR 0012](0012-go-and-rust.md), [ADR 0015](0015-local-web-ui.md), [ADR 0016](0016-jdk-range.md), [ADR 0017](0017-async-project-problems.md), [ADR 0018](0018-editor-code-intelligence.md) |

## Context

The owner wants a kind of project problem where you build a small running service: it has its own dependencies, calls third-party APIs that fail in realistic ways, may own a database whose schema you change, and is judged by what it answers over HTTP. The code base today gives none of that:

- **Grading calls methods.** `cstudy submit` sends a class job through the runner protocol: the runner constructs the entry class and calls the operations of a case, and the core's `ops` comparator judges the outputs ([ADR 0014](0014-project-problems.md), [Grading job](../specs/runners.md#grading-job)). Nothing addresses a process or an HTTP endpoint.
- **Nothing is installed per project.** ADR 0014 rejected a venv or `node_modules` per project because every start would need the network, and rejected Vitest and Jest for needing a network install. Check S15 rejects dependencies in a starter (`package.json` with `dependencies`, a `[project]` table in `pyproject.toml`) and rejects lock files (`LOCK_FILES` in `domain/project_checks.py`). A Python folder's `.venv` is a link to the shared venv.
- **A lock file is a thing to ignore.** `is_untracked` in `domain/workspace_projects.py` names `uv.lock` and `Cargo.lock`, the workspace template's `.gitignore` ignores `projects/*/uv.lock` and `projects/*/Cargo.lock`, and `archive_folder` deletes what `is_untracked` names before it moves a folder.
- **The schema assumes an entry class.** `schemas/meta.schema.json` requires `signature` for every problem and `project.entry` for every project, requires `time_class` and `space_class` on every approach outside `concurrent`, and S14 requires track `practical` and the `ops` comparator.
- **User code runs as you, with your environment.** There is a hang guard and no sandbox ([PRD](../prd.md#5-technical-overview)). `_environment` in `adapters/subprocess_runner.py` hands a runner `{**os.environ, ...}`, or inherits outright when a launch sets no variables, so a token in your shell reaches user code today. [P2](#phases) changes this for every problem.
- **Process ownership has precedents.** Every process `cstudy` starts leads its own process group, `_kill_group` in `adapters/subprocess_runner.py` kills it, and `OrphanGuard` in `adapters/process_liveness.py` kills it if `cstudy` dies ([Process lifecycle](../specs/runners.md#process-lifecycle)). Language servers live as long as an attempt's page ([Lifecycle and limits](../specs/web-ui.md#lifecycle-and-limits), `entrypoints/web/language_server.py`). Containers are outside all of this: they outlive a process group.

The name "service project" is new in the repository. `cache-service` and `notification-service` are catalog slugs and do not collide. Three other names do collide, and this ADR resolves them in [Names](#names).

No spike has run. Every number in this ADR is an expectation until a phase measures it, and each is marked so.

## Decision

### Decided by the owner

| # | Decision (2026-11-05) |
|---|-----------------------|
| O1 | cstudy works on your own machine and needs the internet only for the obvious reasons: installing the app and its dependencies and, once built, opt-in AI review with your own key ([ADR 0021](0021-ai-reviewed-problems.md)). Installing dependencies does not break the rule. [NFR-6](../prd.md) now says this. ADR 0014's rejection of per-project installs is superseded in part, for this kind of problem. Existing problems do not change |
| O2 | A project problem may have its own dependencies. Either you run the install or cstudy runs it automatically when the problem begins |
| O3 | One general mock server is built into cstudy, written in Python because that matches cstudy, so every language version of a problem shares it |
| O4 | Any project problem can use it by defining configuration files. A project can have several mock servers, all running locally. Their addresses are settled by [O15](#decided-by-the-owner): stable names on the stack's network, which replaces the earlier dynamically assigned ports |
| O5 | Scenarios include a 429 rate limit, alongside outage (503), slow and malformed |
| O6 | The first problem keeps this general concept and is written from scratch: inventory counted per day plus time slots from a third-party vendor, served from one API, with vendor failure handling. The domain is original to cstudy: a coworking space, with desk passes counted per day and meeting rooms booked in time slots from a room vendor. A second vendor with a different response shape is a later level, which is what several mock servers are for |
| O7 | Language order for these problems: TypeScript, then Python, then Kotlin and Java, then Go, then Rust (maybe; decided when reached) |
| O8 | Implementation waits. This documents the plan only |
| O9 | The database and the migration tool are both defined per project, as part of problem design, and cstudy requires neither. A TypeScript problem may use what is common in that ecosystem, and a Python problem could use Alembic. The owner prefers Liquibase, which is a preference, neither a default nor a requirement. A problem may pick SQLite or Postgres according to what it teaches. The manifest and the grading design stay tool-neutral: a declared command, with no tool-specific field |
| O10 | Service projects can run a real database. The problem has a way to run migrations, seed data arrives through migrations, and the service reads the database live. Postgres is wanted because SQLite is too limited for what some problems teach |
| O11 | Docker is how service projects get backing services, such as Postgres, Redis and LocalStack. Under O15 every service project needs Docker, whether or not it declares services. The existing bank problems never do |
| O12 | A service project has standard lifecycle commands whose contents the problem's designer defines. Names are fixed, contents are free, and cstudy calls only the standard names |
| O13 | The CLI and the web UI list what a problem depends on, so you know before starting: language and toolchain version, Docker, each service with its image download size, mock servers by name, the package manager and approximate install size, total download, approximate memory, and whether each requirement is met on this machine, with the reason when it is not. This reuses ADR 0016's display of the JDK range rather than adding a parallel concept |
| O14 | When a problem needs Docker: if Docker is installed but not running, cstudy starts it; if Docker is not installed, cstudy asks you to install it and gives instructions. cstudy does not install Docker itself |
| O15 | **Service projects always run in Docker, as their sandbox.** Bank problems stay native, need no Docker, and do not change. This **supersedes the earlier position** of this ADR: your app on the host, mock servers as native host processes, Docker only for problems with services, and dynamic ports. The reasons: per-project dependencies mean running third-party code and install scripts, and security catalog starters contain deliberate flaws, so an unfixed SSRF starter could otherwise reach your LAN or a cloud metadata endpoint. Docker gives a boundary at the project folder: nothing above it is visible |

### Names

| Name in the brief | What the repository already means by it | Decision |
|-------------------|------------------------------------------|----------|
| `cstudy mock <slug>` | [`cstudy mock`](../specs/cli.md#cstudy-mock) exists: a timed practice session with a shared timer and locked hints. `mock` is also an attempt mode and a Web UI view | The new foreground command is `cstudy dev <slug>`. It also starts services and runs `bootstrap`, so "mock" would undersell it. Prose says "mock server", never a bare "mock" |
| `commands.init` | [`cstudy init`](../specs/installation-and-workspaces.md#cstudy-init) creates a workspace | The command is `commands.install`, which says what it does. `install` is no `cstudy` verb, and the doctor's [`installs` row](../specs/cli.md#the-installs-row) counts cstudy's own installs, a different thing |
| `commands.test` | [`cstudy test`](../specs/cli.md#cstudy-test) exists | Kept on purpose: `cstudy test` on a service project calls it |
| `commands.run` | The Web UI calls a test or submission a run (`POST /api/v1/runs`) | Kept: "run" as a verb on an app is plain, and the manifest key cannot be confused with an API route |

### Shape

- **A service project is `kind: project` with `project.grading: http`.** It has one language per problem, levels and `cstudy submit`. `project.entry`, `project.tests`, `signature`, generated test files and complexity classes do not apply to it, so the schema's requirements become conditional at implementation ([below](#schema-rules-to-relax)).
- **Everything runs in one compose stack.** Your app, the mock servers and backing services share one network, so a mock server has a stable name such as `http://room-vendor:8080`. `.env` therefore ships ready-made in the starter, an ordinary visible file with no secrets.
- **Only your project folder is visible.** It is bind-mounted at the same absolute path as on your machine, so paths match. Parent folders, `.cs/` and your home are not there. The toolchain links of existing project folders do not apply to these projects.
- **cstudy calls only standard commands, inside the app container.** `install`, `bootstrap`, `run` and `test`, and optionally `reset` and `grade_setup`, as argument lists ([spec](../specs/service-projects.md#lifecycle-commands)).
- **The core owns the infrastructure.** The generated compose file, hardening, networks, labels and cleanup belong to cstudy. A command must not start a service, or leftovers fall apart. Commands run after services are up.
- **Trust follows location.** `commands` live in the problem's manifest, and `grade_setup`, hidden data and mock configs live outside the starter. A starter script that a command points to can be edited by you, which is acceptable for `install`, `bootstrap`, `run` and `test`, because the grader judges behavior over HTTP. It is not acceptable for `grade_setup`, which therefore must live in the problem's own files. The grader stays outside the app container, and hidden material never enters it.
- **Existing problems are unchanged**, apart from the environment allowlist of [P2](#phases). The bank problems, and every other kind, keep their per-language runners and paths.
- **Language support moves to templates.** The per-language decisions, the toolchain image and the install command, live in project templates under `cli/src/coding_study/adapters/templates/`, so a new language needs a new template and one row in `PROJECT_TEMPLATE_LANGUAGES` (`domain/scaffold.py`), and no new core logic.

### Honest limits

| Limit | What it means |
|-------|---------------|
| The project folder stays writable by the code | The sandbox protects everything else from your code. A flawed starter or a bad dependency can still damage or read the project folder, which is why that folder is versioned practice work and holds no secrets |
| On Linux, access to Docker is effectively root | Being in the `docker` group grants this. cstudy cannot reduce it, never mounts the socket into a container, and says so in the install message |
| It is a boundary against accidents and bad dependencies, not a hardened multi-tenant jail | Container isolation shares a kernel. It is the wall between your machine and code you run on purpose |
| `install` has the internet | An install script can send out what it can read, which is the project folder and nothing above it |

### The first problem and later ones

The sketch is in the [spec](../specs/service-projects.md#the-first-problem). It is original to cstudy, in line with [ADR 0004](0004-original-problem-wording.md). The stack per language is chosen at authoring time, with Express or an equivalent now allowed. Open-ended design discussion cannot be auto-graded and goes in `solutions/explanation.md`. Data-driven problems stay in the coworking theme, and their domain, database and migration tool are chosen at authoring.

### Open to confirm

Recommended by the assistant and not contradicted by the owner. Each is confirmed when its phase starts. R3 and R21 are withdrawn because O15 removes what they solved, the generated `.env` and `.env.local`, and their numbers are not reused.

| # | Recommendation | Alternative | Trade-off |
|---|----------------|-------------|-----------|
| R1 | Install automatically at problem start, in a one-off app container with internet, with visible progress and a clear retry on failure. Install again when the lock file's digest changes | You run the install, as a printed command | Automatic means one less step and no stale dependencies; it also means a network wait at start, shown first by [O13](#decided-by-the-owner) |
| R2 | No daemon. cstudy owns a stack for the duration of each `test` and `submit`; `cstudy dev <slug>` runs one in the foreground for development; the Web UI runs one on request while the attempt page is open. `cstudy start` exits, so it starts nothing and prints the `cstudy dev` command | A daemon started by `cstudy start` | A daemon survives between commands and needs no second terminal, but it is an unowned process; the sweep then has no owner to check |
| R4 | HTTP black-box grading first. The grader runs on your machine, outside every container. It reaches your app through its published port, polls a health path, and for each case resets the mock servers, sets scenarios, sends a request, compares the response, optionally asserts on the mock server's request log, then stops the stack. One piece of core code covers every language. It emits the same `--events`, so the CLI and the Web UI render it. Existing entry-class problems keep their path. `verify` (D1, D3, D9) runs the reference the same way | Entry-class grading with a facade | The facade is cheaper now but does not test the API. HTTP grading costs a new kind of run, and your app must read its port from the environment and expose a health path. Because no user table is named, it is also what makes [R8](#open-to-confirm) possible |
| R5 | `project.services` names a problem-owned compose file, tool-neutral, so any image can be used. It holds only backing services, and cstudy merges it with the file it generates. Images are pinned by digest. You cannot edit what grading trusts | A field per engine | Tool-neutral keeps Postgres, Redis and LocalStack out of the core; it needs static checks on a file format cstudy does not own |
| R6 | `docker compose -p <unique name>` with `up --wait` against healthchecks and `down -v` at the end. Dev uses a persistent named volume; each graded run uses a fresh project name and no reused volume. These compose behaviors are verified by the spike | Plain `docker run` calls | Compose already gives names, health waits and one-command teardown |
| R7 | Leftovers. Containers outlive a crashed cstudy, so `OrphanGuard` and group kill do **not** cover them. Everything cstudy starts is labeled, a sweep runs at the next command, and a doctor row and its fix remove leftovers by label only, never another container or volume. This is a stated requirement, given earlier memory exhaustion on the owner's machine | Rely on `down` and `OrphanGuard` alone | A crash would leave containers holding memory with nothing to find them. Between a crash and the next `cstudy` command they still hold it; the spike decides whether the guard also runs `down` |
| R8 | Grading a schema you design. The problem ships a baseline schema and data as the starter's migrations. `grade_setup`, problem-owned, applies only the baseline with the problem's own tool and loads hidden data; `bootstrap` then applies the rest, because the tool's tracking table already records the baseline. Your migrations must carry existing data forward, which tests real data migrations. Requests and comparisons stay black-box, so no user table is named. Migrating from empty is checked too. To be proven on the first data-driven problem with its chosen tool | Hidden cases that write to your tables | They would dictate your schema, which is the thing being practiced |
| R9 | Contract tables, a design point. For live-read checks a problem may declare tables that the grader writes to mid-run and that you may not rename. Otherwise changes go through the API or the mock servers | No contract tables | A contract table limits your schema freedom, so it is used only when neither the API nor a mock server can make the change |
| R10 | Reset stays engine-neutral: an optional `commands.reset`, otherwise data resets per run. PostgreSQL's `CREATE DATABASE ... TEMPLATE` is an example of such a command, not a core feature, and is measured when first used | A core reset per engine | Core stays small; each problem carries its own script |
| R11 | A parallel case: N requests against limited capacity, asserting that exactly M succeed and the final state through the API. It gives language-neutral concurrency grading, which is what SQLite cannot show | Stress cases in each language's runner | Runners are per-language work and need an entry class; a parallel case needs neither. As with stress runs, a pass is not a proof of safety |
| R12 | Doctor: a row checks for a running engine and `docker compose` v2. Any engine that provides this works; Docker Desktop is verified at minimum, and no other is claimed until tested. Without it, service projects show as unavailable with the reason, and the row is `WARN`, never `FAIL`, as Go's and Rust's are, since Docker is optional for cstudy overall | `FAIL` | `FAIL` would make `cstudy doctor` exit 4 for everyone who never starts such a problem |
| R13 | Images pull at problem start with visible progress, as a dependency install does, and run with no internet afterwards, which fits [O1](#decided-by-the-owner). The download size is shown before pulling, and each problem records its image sizes | Pull on first `test` | Later and more surprising |
| R14 | One stack per attempt, stopped when the run or the attempt page ends, with memory limits on every container. The Web UI starts a stack only on request | A stack from page open | Docker's VM and heavy images such as LocalStack cost real memory |
| R15 | Compose files, mock configs and hidden seeds stay in the problem's own files, outside the starter. Anything rendered from them lands under `.cs/runs/<run>/`, one of the hidden directories, and is mounted read-only into the mock container only. `grade_setup` and hidden data never appear in the app container | Copies in `.cs/` that any container can see | A copy that a container can read adds a place to hide |
| R16 | The exact command set and [contract](../specs/service-projects.md#contract): `install`, `bootstrap`, `run`, `test`, optional `reset` and `grade_setup`, as argument lists, with a script for anything longer | More commands, or shell strings | Fewer commands keep the manifest small; shell strings add quoting and a shell to every image |
| R17 | The dependency list comes from a small declared `project.requires` block plus what cstudy derives from the compose file and lock file. A static check fails when they disagree, so the list cannot drift, and `verify` checks measured sizes against it. The problem listing shows a short marker with a filter for problems that need nothing extra, the detail view shows it in full, and Start shows the summary before any download and asks for confirmation only when something will download or a requirement is missing, with `--yes` for scripts | Derive everything at display time | Sizes need a registry or a measurement; `cstudy list` has a 500 ms budget (NFR-2) |
| R18 | `cstudy test` on a service project runs `commands.test`, then the visible HTTP cases of the unlocked levels as feedback. No native test file is generated | Generated tests per language, as ADR 0014 does | Generation is per-language work in every phase, which the single grader exists to avoid. The cost: opening a level writes no test file, and the visible cases are not native tests you can debug |
| R19 | A migration that fails in `cstudy submit` is reported as an install failure is, with its output, and otherwise as code that does not load: the submission is stored and exits 2. A failed `install` exits 4 and stores nothing | Exit 4 for both | Your migration is your code, so storing it matches ADR 0014's rule; exit 4 would call your bug an environment problem |
| R20 | A first level asks for one small change as well as orientation, so the starter does not pass it untouched | A level the starter already passes | `cstudy done` takes a rating once level 1 passes, so a free pass would weaken it |
| R22 | Docker's states: not installed, installed and stopped, running, and on Linux installed without permission, each with its own message. cstudy starts the engine only when you start or run a service project, and from `doctor --fix`; never from listing or viewing a problem, or from plain `doctor`, because starting Docker's VM costs real memory. It says it is starting, shows progress, waits up to a stated timeout and reports clearly if the engine did not come up. It never runs `sudo`, printing the command instead, and never stops the engine, only its own labeled stacks. Install instructions are one short message per platform with a link to Docker's install page, kept in one place so the requirements summary, `doctor` and the Web UI's Start match. The start mechanism per platform is verified at implementation ([spec](../specs/service-projects.md#docker-states)) | Start the engine at `doctor` or whenever a problem is shown | Earlier and less waiting at Start, at the cost of a VM's memory for someone who is only reading |

Added with O15, for the same confirmation:

| # | Recommendation | Alternative | Trade-off |
|---|----------------|-------------|-----------|
| R23 | Hardening of every container cstudy generates: non-root (your UID on Linux), `cap_drop: ALL`, `no-new-privileges`, a read-only root filesystem plus tmpfs, memory and pids limits, the Docker socket never mounted, and an explicit environment only, so nothing from your machine leaks in, especially real API keys. Problem-owned services get the limits and `no-new-privileges`, since an engine such as Postgres needs its own user and writable paths | Docker's defaults | The limits also protect a small machine from runaway memory. A read-only root breaks a tool that writes outside the project and tmpfs, which the spike looks for |
| R24 | Network. `install` may use the internet; `run` and `test` have no egress. **Known catch, for the spike:** a Docker `internal: true` network probably cannot publish ports (unverified), so the likely design adds a small forwarder container joined to both an `internal` network and an ordinary one. It holds no user code and publishes on `127.0.0.1` with a dynamic host port: your app's port and, for the grader alone, the token-protected mock server control port | A grader inside the network, which needs no control port on your machine but puts cases in a container | The forwarder keeps hidden cases on your machine at the cost of one small container per stack. "Only the app's port is published" holds for what a learner uses; the control port is the one exception, and a grader inside the network would remove it |
| R25 | One mock container: a pinned Python image, with cstudy's mock server code mounted read-only from cstudy and the configs mounted read-only. Each mock server's name is a network alias of that container, and the process picks the mock server from the request's `Host`, so every one answers on port 8080 at its own name | One container per mock server | One process costs less memory and keeps one control interface. A client that rewrites `Host` gets a clear 404. Several containers isolate a crash, which a stateless server hardly needs |
| R26 | `.env` is a starter file holding exactly `project.env`, which S19 checks: the app's port, stable URLs and fake keys, so it is tracked, hashed and archived like any file. The app container's environment is `project.env` plus a few fixed variables. `.env.local` is dropped: with fixed values and no secrets you edit `.env` itself | Keep `.env.local` | A second file would hide nothing and cost hash and archive rules |
| R27 | Per-language toolchain images, named in `project.image`, pinned by digest and pulled on demand, shown in the requirements list before download. Pin the multi-architecture index so macOS on arm64 and Linux on amd64 share one pin. The host needs no Node, uv or JDK for a service project | Images built locally on start | Building needs a registry and a Dockerfile anyway, and costs minutes. Official images may not hold the package manager (a Python image has no uv), which the spike settles: an image of cstudy's own, or a step in `install` |
| R28 | **Riskiest part.** Code intelligence for service projects runs the language server inside the container through `docker exec -i`, with paths matching because of the same-path mount. The server is `.cs/lsp/` mounted read-only, or a toolchain inside the image, which the spike settles: basedpyright needs Node, and a Python image has none | A language server on your machine reading the project folder | On your machine, `.venv` points at an interpreter that exists only in the container and native packages are Linux builds. In a container, hidden directories simply do not exist, a stronger guarantee than today's filter, but there is more to go wrong ([spec](../specs/service-projects.md#language-servers)) |
| R29 | Your own IDE uses a generated `devcontainer.json`, and debugging goes through a port published on `127.0.0.1` by `cstudy dev --debug`, in a dev stack only | A local toolchain matched to the image | A generated config avoids two toolchains drifting apart. It does not help LazyVim directly, which the spike tries with a per-project server command |
| R30 | `node_modules` and `.venv` stay in the project folder on the bind mount at first, so your editor can read them. It is slower on macOS, and a volume is faster but invisible to your editor. The spike measures the trade-off | A volume from the start | Speed against an editor that can read dependencies |
| R31 | `cstudy dev` runs `commands.run` by default, since your app cannot run outside the stack and still reach the mock servers. `--no-run` keeps the container idle for an IDE or debugger. `cstudy dev --exec [--network] -- <command>` runs one command in a one-off app container, which is how you add a dependency with `--network` | A new verb per action | One new verb stays one new verb, at the cost of a longer flag list |
| R32 | Separate early phase, for **all problems**: replace the inherited environment with an allowlist, so tokens do not leak into user code. Today's behavior is `{**os.environ, ...}` in `adapters/subprocess_runner.py`, and the other launches named in [P2](#phases) inherit too. A config key adds names you want to pass on | Sandbox only service projects and leave native runs as they are | The allowlist can surprise someone relying on an inherited variable. It stops environment leaks only: a native problem still runs as you and can read your files |
| R33 | Mock server extensions: SSE streaming with chunk timing and mid-stream drops; matching on request bodies; assertions on logged request bodies, including a byte-prefix check across requests; bodies that use values known at run time. A local mock LLM provider is then just mock config data, with no key or cost, and a fake key is injected. Provider response shapes drift, so each such config records its shape version ([spec](../specs/service-projects.md#extensions)) | A second, LLM-specific mock server | One program stays one program |
| R34 | Multi-step HTTP cases: a later request can use values captured from earlier responses, for login and OIDC flows. Per-request token signing for a mock identity provider is not in the mock server's scope: use a service container, decided at the first identity problem | Signing inside the mock server | Signing would make the deliberately stateless mock server a small identity provider |
| R35 | `grade_setup` runs in its own short-lived container of the same image, with `{problem}/grading/` read-only and the project folder read-only, and it exits before the app container starts. Data it loads does reach the database your app reads, which is inherent in [R8](#open-to-confirm); the script and its files do not | Run it on your machine | It would need your machine to hold the migration tool and to reach a port of the database |

### Schema rules to relax

At implementation, for `grading: http`. Until then `schemas/meta.schema.json` stays as it is.

| Rule today | Where | Change |
|------------|-------|--------|
| `signature` required on every problem, with `function` or `class` by kind | `required` and `allOf` in `schemas/meta.schema.json` | Not used |
| `project.entry` required | `$defs/project` | Not used |
| `time_class` and `space_class` required on every approach except `concurrent` | `allOf` in `schemas/meta.schema.json` | Meaningless for an HTTP problem, so not used |
| Projects are on track `practical` and use the `ops` comparator | [S14](../specs/authoring.md#static---static-runs-only-these) | A `debugging` project-size problem needs other tracks ([ADR 0020](0020-catalog-labels.md)); the comparator is per case |

## Phases

| Phase | Scope |
|-------|-------|
| P1 | **Spike**, on macOS and Linux, [below](#the-p1-spike). If it fails, the owner is told before anything is built |
| P2 | Environment allowlist for **all** problems, in place of the inherited environment: `_environment` in `adapters/subprocess_runner.py`, `adapters/languages/go/toolchain.py`, `adapters/languages/rust/toolchain.py`, `adapters/languages/rust/project_suite.py`, `adapters/languages/jvm/gradle.py`, `entrypoints/web/language_server.py` and `entrypoints/web/code_intelligence.py`. `entrypoints/web/children.py` starts `cstudy` itself, which needs its configuration, so the cut sits where a child runs user or toolchain code. Independent of the rest, so it can ship early |
| P3 | Sandbox runtime: the generated compose file and its hardening, networks, labels, sweep, `docker` and `docker leftovers` doctor rows, Docker start and install messages, image pull, a CI job with Docker |
| P4 | The lifecycle commands and their contract; dependency install and lock rules; the TypeScript and Python service templates with `.env`; `project.requires` with its static check and the dependency list in `cstudy show`, `cstudy list` and `cstudy start` |
| P5 | The Python mock server, `schemas/mock.schema.json`, its container and `cstudy dev` |
| P6 | The HTTP grader, with `verify` and CI wired in. CI installs from the network, so it caches the pnpm store and the uv cache by lock digest |
| P7 | The first problem in TypeScript |
| P8 | The Python version of the first problem |
| P9 | Code intelligence in the container, generated IDE files, and Web UI: stack status, the scenario picker, and the dependency list in the Problems view, the Problem view and the Start dialog |
| P10 | Data-driven problems, TypeScript then Python, each choosing its own database and migration tool: `project.services` and S21, which proves the flow of R8, with parallel cases and any contract table. SQLite needs Docker here as well, like every service project |
| P11 | Mock server extensions and multi-step cases, with the first project-size security and AI problems ([ADR 0020](0020-catalog-labels.md#the-map-by-size)) |
| P12 | Kotlin and Java templates and problems. Settles Gradle's `--offline` for these problems |
| P13 | Go template and problems. Settles `GOPROXY=off` and vendored modules for these problems |
| P14 | Rust template and problems (maybe; decided when reached). Settles vendored crates for these problems |
| Later | `scope: system` learner-built systems ([below](#later-learner-built-systems)) |

Each phase gets its docs and, at release, a website message. This plan runs after or around the code intelligence releases of [ADR 0018's Phases](0018-editor-code-intelligence.md#phases) (1 Python and TypeScript, 2 Java and Kotlin, 3 Go and Rust) unless the owner reorders it. The two share a language order only loosely: ADR 0018 puts Python and TypeScript in one release, and O7 here puts TypeScript first.

### The P1 spike

Measured on macOS (Docker Desktop) and Linux, on an otherwise quiet machine. The spike reports numbers and does not build product code. If it fails, the owner hears before anything is built. **Named fallback, not chosen:** OS sandboxes, `sandbox-exec` on macOS, which is deprecated, and bubblewrap on Linux.

| Question | What to find out |
|----------|------------------|
| Code intelligence in the container | basedpyright and typescript-language-server through `docker exec -i` with the same-path mount: time to first diagnostics, hover and definition into `node_modules`. A definition into a standard library inside the image lands on a path your machine cannot read, and the page's read-only library tabs need an answer. Whether killing `docker exec` stops the server, or only closing its standard input does (unverified) |
| Your IDE | A generated `devcontainer.json` in VS Code and in IntelliJ, and a per-project server command in LazyVim |
| Debugger | Node's inspector and debugpy through a published port, with breakpoints resolving on the same paths |
| File speed | An install and a test run on a bind mount against a volume, for `node_modules` and `.venv`. Whether file-change events reach a watcher inside the container |
| Run latency | `cstudy test` and `cstudy submit` shapes against the [feedback targets](../prd.md#non-functional-requirements) of NFR-1 and NFR-11: `up --wait`, then a case. Whether reusing a running dev stack for `cstudy test` is worth it |
| Memory | Docker's VM, the app, mock and forwarder containers, then Postgres, Redis and LocalStack. A dev stack and a graded stack together. Total limits that fit an 18 GB machine |
| The network catch | Whether an `internal: true` network can publish ports on each platform; the forwarder; that a container cannot reach a public address, a LAN address, a cloud metadata address, or Docker Desktop's `host.docker.internal` |
| Compose behaviors | `-p`, `--wait`, `127.0.0.1::<port>`, `port`, `down -v`, labels on networks and volumes through an override, the hardening of R23 on each official image, non-root ownership of bind-mounted files |
| Mounts | Whether Docker Desktop shares the paths cstudy needs by default: a Homebrew prefix may not be shared, and then the mock code must be copied under `.cs/runs/<run>/`. A workspace outside the shared paths, and SELinux labels on Linux |
| CI | Linux runners have Docker, and macOS runners may not by default |

## Consequences

- NFR-6 now says what the owner meant, and the PRD's "no network at runtime" is qualified by it. A service project installs dependencies and pulls images at start. Everything else about NFR-6 is unchanged.
- **Docker becomes a requirement for a class of problems**, SQLite ones included. Docker Desktop's license requires a paid plan at larger companies; verify the current terms before saying anything more specific in the docs. Other engines are claimed only once tested (R12).
- Service projects cannot meet NFR-1's project targets: starting a stack plus real waits for `Retry-After` and delays take seconds, not 1.0 s. NFR-1 gains a target of its own once P6 measures it. As for D6, D7 and D10 in [ADR 0017](0017-async-project-problems.md), the new checks stay outside NFR-3's 30 s per problem.
- A service case runs on the real clock, against ADR 0017's "virtual time wherever code waits". `project.clock: virtual` is refused with `grading: http`, and a static limit plus a determinism check keep real waits short and stable.
- New surface, all planned: `project.grading`, `image`, `commands`, `app`, `env`, `mocks`, `services`, `requires`; `schemas/mock.schema.json`; HTTP, multi-step and parallel case shapes in `tests.json`; `cstudy dev`; `cstudy start --yes`; `cstudy list --needs`; checks S19 to S23 and D11; `docker` and `docker leftovers` doctor rows.
- `is_untracked` becomes aware of the kind of project, because a service project's `uv.lock` is a file grading trusts, while a bank project's is tool output. A service starter's own `.gitignore` re-includes its lock file.
- `cstudy start` writes no `.venv` link for a service project, and `doctor --fix` restores none, since its `.venv` is a real directory in the folder. The risk ADR 0014 guarded against, `uv run` deleting the shared venv through the link, does not apply there. The same goes for every other toolchain link and for the JDK range: the image is the toolchain.
- Disk grows per project (`node_modules`, `.venv`), and `cstudy start --fresh` already removes those through `remove_untracked`. There is no `cstudy reset` and no remove command ([Cleanup](../specs/service-projects.md#cleanup)).
- A dev stack and a graded stack can overlap for the length of a run. Declared memory limits bound each, and the spike measures the total.
- Hidden data and references stay out of the app container for every problem, your own under `<workspace>/problems/` included, because no parent folder is mounted. That is stronger than today's [hidden directories](../specs/web-ui.md#hidden-directories), as long as the language server runs inside the container too.
- "No network" stops being an honor rule for authors: the network enforces it for `run` and `test`, and D11 probes it.
- `docs/README.md` indexes ADRs and `docs/architecture.md` describes adapters. Both change when the first phase lands.

## Later: learner-built systems

`scope: system` in [ADR 0020](0020-catalog-labels.md) names problems where you build several services. They are **not designed here**: this plan has one `run`, one health path and one `port_env`. The compose network at least makes them possible, since several of your services could share it under stable names. That design waits, with these questions open: how several `commands.run` are declared, what health means for a system, and which service a case addresses.

## Revisit

| Trigger | What to reconsider |
|---------|--------------------|
| The P1 spike fails, or Docker's memory cost proves too high on an 18 GB machine | Report to the owner before building. The fallback is the owner's call |
| Code intelligence or the IDE flow in the container proves unusable | The riskiest part of O15: report to the owner, with OS sandboxes as the named fallback |
| A hand-written `commands.test` proves too costly to author, or learners miss native tests per level | Generated tests per language, from the visible cases |
| The `grade_setup` flow cannot work with a problem's chosen migration tool | That problem's tool, or a contract table |
| A problem needs a stateful mock server, or path templates | Extending the mock config, which is deliberately stateless |
| The first identity problem needs signed tokens | A service container chosen at that point (R34) |
| A problem needs a parallel case's expected count to vary | A checker over the responses |
| Real waits push a submission past what is tolerable | Lower limits, or running your app on a controllable clock where the language allows |

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Your app and mock servers native on your machine, with Docker only for services | The earlier position of this ADR, superseded by O15: third-party code and deliberately flawed starters would run with your machine in reach |
| OS sandboxes per platform (`sandbox-exec`, bubblewrap) | Not chosen. Named as the fallback if the spike fails. Two mechanisms, one of them deprecated |
| A cstudy-managed native Postgres, from prebuilt binaries | Rejected by the owner: cstudy should not run a Postgres server directly on your machine, and Docker unlocks many services, such as Postgres, LocalStack and Redis, where a native approach would solve only one |
| Mock servers in the language of each problem | Rejected by O3: one written per language multiplies the work and the behaviors to keep equal |
| A third-party mock server tool | A dependency cstudy would have to install and pin, with scenario rules of its own |
| Scenario choice as a query parameter of the mocked API | It would leak into the vendor's contract, so code could read or fake it |
| Stacks started by `cstudy start` | `cstudy start` exits, so they would be unowned |
| A per-language dependency table in the core | A new language would need core code; templates hold the same decisions |
| Tool-specific fields such as `migrations: liquibase` | Rejected by O9: the core has no knowledge of any migration tool |
| Grading through the native test framework | The second judge that ADR 0010 and ADR 0014 rejected: editable code would give the verdict |
