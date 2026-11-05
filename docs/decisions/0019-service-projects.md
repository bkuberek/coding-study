# ADR 0019: Service projects run a real local app against mock servers and optional backing services, graded over HTTP

| Field | Value |
|-------|-------|
| Status | Accepted as a plan. Nothing here is built, and implementation has not started. The items under [Open to confirm](#open-to-confirm) are confirmed when their phase starts |
| Date | 2026-11-05 |
| Spec | [service-projects](../specs/service-projects.md) (planned). Today's behavior stays in [problem-format](../specs/problem-format.md#project-problems), [runners](../specs/runners.md#project-jobs), [authoring](../specs/authoring.md#project-problems), [cli](../specs/cli.md#cstudy-submit), [installation-and-workspaces](../specs/installation-and-workspaces.md#project-folders) and [web-ui](../specs/web-ui.md#file-api-rules), each of which carries a forward pointer until its phase lands |
| Supersedes in part | [ADR 0014](0014-project-problems.md): for service projects only, the rejection of a venv or `node_modules` per project and of test tools that need a network install. Existing problems do not change |
| Amends | [PRD](../prd.md) (NFR-6: what "offline" means, as the owner defined it) |
| Builds on | [ADR 0001](0001-data-driven-tests.md), [ADR 0004](0004-original-problem-wording.md), [ADR 0012](0012-go-and-rust.md), [ADR 0015](0015-local-web-ui.md), [ADR 0016](0016-jdk-range.md), [ADR 0017](0017-async-project-problems.md), [ADR 0018](0018-editor-code-intelligence.md) |

## Context

The owner wants a kind of project problem where you build a small running service: it has its own dependencies, calls third-party APIs that fail in realistic ways, may own a database whose schema you change, and is judged by what it answers over HTTP. The code base today gives none of that:

- **Grading calls methods.** `cstudy submit` sends a class job through the runner protocol: the runner constructs the entry class and calls the operations of a case, and the core's `ops` comparator judges the outputs ([ADR 0014](0014-project-problems.md), [Grading job](../specs/runners.md#grading-job)). Nothing addresses a process or an HTTP endpoint.
- **Nothing is installed per project.** ADR 0014 rejected a venv or `node_modules` per project because every start would need the network, and rejected Vitest and Jest for needing a network install. Check S15 rejects dependencies in a starter (`package.json` with `dependencies`, a `[project]` table in `pyproject.toml`) and rejects lock files (`LOCK_FILES` in `domain/project_checks.py`). A Python folder's `.venv` is a link to the shared venv.
- **A lock file is a thing to ignore.** `is_untracked` in `domain/workspace_projects.py` names `uv.lock` and `Cargo.lock`, the workspace template's `.gitignore` ignores `projects/*/uv.lock` and `projects/*/Cargo.lock`, and `archive_folder` deletes what `is_untracked` names before it moves a folder.
- **A file is tracked or it does not exist.** `is_untracked` both hides a path from the file API and refuses it. There is no visible, read-only, unhashed file.
- **The schema assumes an entry class.** `schemas/meta.schema.json` requires `signature` for every problem and `project.entry` for every project, and S14 requires the `ops` comparator.
- **Process ownership has precedents.** Every process `cstudy` starts leads its own process group, `_kill_group` in `adapters/subprocess_runner.py` kills it, and `OrphanGuard` in `adapters/process_liveness.py` kills it if `cstudy` dies ([Process lifecycle](../specs/runners.md#process-lifecycle)). Language servers live as long as an attempt's page ([Lifecycle and limits](../specs/web-ui.md#lifecycle-and-limits), `entrypoints/web/language_server.py`). Containers are outside all of this: they outlive a process group.

The name "service project" is new in the repository. `cache-service` and `notification-service` are catalog slugs and do not collide. Three other names do collide, and this ADR resolves them in [Names](#names).

No spike has run. Every number in this ADR is an expectation until a phase measures it, and each is marked so.

## Decision

### Decided by the owner

| # | Decision (2026-11-05) |
|---|-----------------------|
| O1 | "Works offline" means cstudy runs on your machine and needs the internet only for the obvious reasons: installing the app and its dependencies. It never meant no installs, and installing dependencies does not break the rule. [NFR-6](../prd.md) now says this. ADR 0014's rejection of per-project installs is superseded in part, for this kind of problem. Existing problems do not change |
| O2 | A project problem may have its own dependencies. Either you run the install or cstudy runs it automatically when the problem begins |
| O3 | One general mock server is built into cstudy, written in Python because that matches cstudy, so every language version of a problem shares it |
| O4 | Any project problem can use it by defining configuration files. A project can have several mock servers. All run locally and get dynamically assigned ports. The owner's words were "dynamic IPs"; this ADR reads them as dynamic ports: every mock server binds `127.0.0.1`, only the port varies, and nothing ever binds `0.0.0.0` |
| O5 | Scenarios include a 429 rate limit, alongside outage (503), slow and malformed |
| O6 | The first problem keeps this general concept and is written from scratch: inventory counted per day plus time slots from a third-party vendor, served from one API, with vendor failure handling. The domain is original to cstudy: a coworking space, with desk passes counted per day and meeting rooms booked in time slots from a room vendor. A second vendor with a different response shape is a later level, which is what several mock servers are for |
| O7 | Language order for these problems: TypeScript, then Python, then Kotlin and Java, then Go, then Rust (maybe; decided when reached) |
| O8 | Implementation waits. This documents the plan only |
| O9 | The database and the migration tool are both defined per project, as part of problem design, and cstudy requires neither. A TypeScript problem may use what is common in that ecosystem, and a Python problem could use Alembic. The owner prefers Liquibase, which is a preference, neither a default nor a requirement. A problem may pick SQLite or Postgres according to what it teaches. The manifest and the grading design stay tool-neutral: a declared command, with no tool-specific field |
| O10 | Service projects can run a real database. The problem has a way to run migrations, seed data arrives through migrations, and the service reads the database live. Postgres is wanted because SQLite is too limited for what some problems teach |
| O11 | Docker is how service projects get backing services, such as Postgres, Redis and LocalStack. It is required only by problems that declare services. A problem with no services, mock-only ones and the existing bank problems included, never needs Docker |
| O12 | A service project has standard lifecycle commands whose contents the problem's designer defines. Names are fixed, contents are free, and cstudy calls only the standard names |
| O13 | The CLI and the web UI list what a problem depends on, so you know before starting: language and toolchain version, whether Docker is needed, each service with its image download size, mock servers by name, the package manager and approximate install size, total download, approximate memory, and whether each requirement is met on this machine, with the reason when it is not. This reuses ADR 0016's display of the JDK range rather than adding a parallel concept |
| O14 | When a problem needs Docker: if Docker is installed but not running, cstudy starts it; if Docker is not installed, cstudy asks you to install it and gives instructions. cstudy does not install Docker itself |

### Names

| Name in the brief | What the repository already means by it | Decision |
|-------------------|------------------------------------------|----------|
| `cstudy mock <slug>` | [`cstudy mock`](../specs/cli.md#cstudy-mock) exists: a timed practice session with a shared timer and locked hints. `mock` is also an attempt mode and a Web UI view | The new foreground command is `cstudy dev <slug>`. It also starts services and runs `bootstrap`, so "mock" would undersell it. Prose says "mock server", never a bare "mock" |
| `commands.init` | [`cstudy init`](../specs/installation-and-workspaces.md#cstudy-init) creates a workspace | The command is `commands.install`, which says what it does. `install` is no `cstudy` verb, and the doctor's [`installs` row](../specs/cli.md#the-installs-row) counts cstudy's own installs, a different thing |
| `commands.test` | [`cstudy test`](../specs/cli.md#cstudy-test) exists | Kept on purpose: `cstudy test` on a service project calls it |
| `commands.run` | The Web UI calls a test or submission a run (`POST /api/v1/runs`) | Kept: "run" as a verb on an app is plain, and the manifest key cannot be confused with an API route |
| "generated" file category | A [generated test file](../specs/problem-format.md#generated-test-files) is tracked, hashed and editable, and `origin: "level"` in the manifest | The new category is a **runtime file**, `origin: "runtime"` |

### Shape

- **A service project is `kind: project` with `project.grading: http`.** It stays on the `practical` track with one language per problem, levels and `cstudy submit`. `project.entry`, `project.tests`, `signature` and generated test files do not apply to it, so the schema's requirements become conditional at implementation.
- **cstudy calls only standard commands.** `install`, `bootstrap`, `run` and `test`, and optionally `reset` and `grade_setup`, as argument lists ([spec](../specs/service-projects.md#lifecycle-commands)).
- **The core owns the infrastructure.** Starting and stopping mock servers and compose stacks, dynamic ports, the runtime `.env`, labels and cleanup belong to cstudy. A command must not start a service, or leftovers and port handling fall apart. Commands run after services are up.
- **Trust follows location.** `commands` live in the problem's manifest, and `grade_setup`, hidden data and mock configs live outside the starter. A starter script that a command points to can be edited by you, which is acceptable for `install`, `bootstrap`, `run` and `test`, because the grader judges behavior over HTTP. It is not acceptable for `grade_setup`, which therefore must live in the problem's own files.
- **Existing problems are unchanged.** The bank problems, and every other kind, keep their per-language runners and paths.
- **Language support moves to templates.** The per-language install decisions live in project templates under `cli/src/coding_study/adapters/templates/`, so a new language needs a new template and one row in `PROJECT_TEMPLATE_LANGUAGES` (`domain/scaffold.py`), and no new core logic. Gradle's `--offline`, Go's `GOPROXY=off` and Rust's vendored crates are decisions of those templates.

### The first problem and later ones

The sketch is in the [spec](../specs/service-projects.md#the-first-problem). It is original to cstudy, in line with [ADR 0004](0004-original-problem-wording.md). The stack per language is chosen at authoring time, with Express or an equivalent now allowed. Open-ended design discussion cannot be auto-graded and goes in `solutions/explanation.md`. Data-driven problems stay in the coworking theme, and their domain, database and migration tool are chosen at authoring.

### Open to confirm

Recommended by the assistant and not contradicted by the owner. Each is confirmed when its phase starts.

| # | Recommendation | Alternative | Trade-off |
|---|----------------|-------------|-----------|
| R1 | Install automatically at problem start, with visible progress and a clear retry on failure. Install again when the lock file's digest changes | You run the install, as a printed command | Automatic means one less step and no stale dependencies; it also means a network wait at start, shown first by [O13](#decided-by-the-owner) |
| R2 | No daemon. cstudy owns mock servers and stacks for the duration of each `test` and `submit`; `cstudy dev <slug>` runs them in the foreground for development from your own terminal or IDE; the Web UI runs them while the attempt page is open, as it does language servers. `cstudy start` exits, so it starts nothing and prints the `cstudy dev` command | A daemon started by `cstudy start` | A daemon survives between commands and needs no second terminal, but it is an unowned process; the group-kill and `OrphanGuard` precedents do not extend to it |
| R3 | `.env` is written, not shipped, because a fixed file cannot hold a port that changes. cstudy writes it when the dev instance starts, preferring the last used port so a running app keeps working. It is a runtime file: visible read-only in the file tree, outside `code_hash`, manifests and archives. Your settings go in `.env.local`, which cstudy never touches. For `test` and `submit`, cstudy injects the variables into the process environment and those win over `.env`; loaders in starters must keep that precedence. Dev and grading instances are separate, so they cannot collide | A shipped `.env` with fixed ports | Fixed ports are simpler to read and collide with anything else on the machine |
| R4 | HTTP black-box grading first. cstudy starts your app with `PORT` and the URLs in the environment, polls a health path, and for each case resets the mock servers, sets scenarios, sends a request, compares the response, optionally asserts on the mock server's request log, then stops the app by group kill. One piece of core code covers every language. It emits the same `--events`, so the CLI and the Web UI render it. Existing entry-class problems keep their path. `verify` (D1, D3, D9) runs the reference the same way | Entry-class grading with a facade | The facade is cheaper now but does not test the API. HTTP grading costs a new kind of run, and your app must read its port from the environment and expose a health path. Because no user table is named, it is also what makes [R8](#open-to-confirm) possible |
| R5 | `project.services` names a problem-owned compose file, tool-neutral, so any image can be used. Images are pinned by digest. You cannot edit what grading trusts | A field per engine | Tool-neutral keeps Postgres, Redis and LocalStack out of the core; it needs static checks on a file format cstudy does not own |
| R6 | `docker compose -p <unique name>` with `up --wait` against healthchecks and `down -v` at the end. Ports publish on loopback with an ephemeral host port (`127.0.0.1::5432`), read back with `docker compose port`. Those URLs join the `.env` and the injected environment. Your app stays on the host at first, so the editor, debugger and native tooling keep working; mock servers stay native Python on the host. Dev uses a persistent named volume; each graded run uses a fresh project name and no reused volume. These compose behaviors are verified by the spike | Running your app in a container too | That gives one network, but inside a container `localhost` is not the host, so it must solve how a containerized app reaches the host's mock servers, possibly by running them in the compose network. A later option. A starter may still ship its own Dockerfile for you to run, ungraded |
| R7 | Leftovers. Containers outlive a crashed cstudy, so `OrphanGuard` and group kill do **not** cover them. Everything cstudy starts is labeled, a sweep runs at the next command, and a doctor row and its fix remove leftovers by label only, never another container or volume. This is a stated requirement, given earlier memory exhaustion on the owner's machine | Rely on `down` and `OrphanGuard` alone | A crash would leave containers holding memory with nothing to find them. Between a crash and the next `cstudy` command they still hold it; the spike decides whether the guard also runs `down` |
| R8 | Grading a schema you design. The problem ships a baseline schema and data as the starter's migrations. `grade_setup`, problem-owned, applies only the baseline with the problem's own tool and loads hidden data; `bootstrap` then applies the rest, because the tool's tracking table already records the baseline. Your migrations must carry existing data forward, which tests real data migrations. Requests and comparisons stay black-box, so no user table is named. Migrating from empty is checked too. To be proven on the first data-driven problem with its chosen tool | Hidden cases that write to your tables | They would dictate your schema, which is the thing being practiced |
| R9 | Contract tables, a design point. For live-read checks a problem may declare tables that the grader writes to mid-run and that you may not rename. Otherwise changes go through the API or the mock servers | No contract tables | A contract table limits your schema freedom, so it is used only when neither the API nor a mock server can make the change |
| R10 | Reset stays engine-neutral: an optional `commands.reset`, otherwise data resets per run. PostgreSQL's `CREATE DATABASE ... TEMPLATE` is an example of such a command, not a core feature, and is measured when first used | A core reset per engine | Core stays small; each problem carries its own script |
| R11 | A parallel case: N requests against limited capacity, asserting that exactly M succeed and the final state through the API. It gives language-neutral concurrency grading, which is what SQLite cannot show | Stress cases in each language's runner | Runners are per-language work and need an entry class; a parallel case needs neither. As with stress runs, a pass is not a proof of safety |
| R12 | Doctor: a row checks for a running engine and `docker compose` v2. Any engine that provides this works; Docker Desktop is verified at minimum, and no other is claimed until tested. Without it, these problems show as unavailable with the reason, and the row is `WARN`, never `FAIL`, as Go's and Rust's are, since Docker is optional for cstudy overall | `FAIL` | `FAIL` would make `cstudy doctor` exit 4 for everyone who never starts such a problem |
| R13 | Images pull at problem start with visible progress, as a dependency install does, and run with no internet afterwards, which fits [O1](#decided-by-the-owner). The download size is shown before pulling, and each problem records its image sizes | Pull on first `test` | Later and more surprising |
| R14 | One stack per attempt, stopped when the run or the attempt page ends, with memory limits declared in the compose file. The Web UI starts a stack only on request | A stack from page open | Docker's VM and heavy images such as LocalStack cost real memory |
| R15 | Compose files and hidden seeds stay in the problem's own files, outside the starter, and get the same treatment as other hidden directories for language servers | Copies in `.cs/` | A copy adds a place to hide |
| R16 | The exact command set and [contract](../specs/service-projects.md#contract): `install`, `bootstrap`, `run`, `test`, optional `reset` and `grade_setup`, as argument lists, with a script for anything longer | More commands, or shell strings | Fewer commands keep the manifest small; shell strings add quoting and a shell to every platform |
| R17 | The dependency list comes from a small declared `project.requires` block plus what cstudy derives from the compose file and lock file. A static check fails when they disagree, so the list cannot drift, and `verify` checks measured sizes against it. The problem listing shows a short marker with a filter for problems that need nothing extra, the detail view shows it in full, and Start shows the summary before any download and asks for confirmation only when something will download or a requirement is missing, with `--yes` for scripts | Derive everything at display time | Sizes need a registry or a measurement; `cstudy list` has a 500 ms budget (NFR-2) |
| R22 | Docker's states: not installed, installed and stopped, running, and on Linux installed without permission, each with its own message. cstudy starts the engine only when you start or run a problem that declares services, and from `doctor --fix`; never from listing or viewing a problem, or from plain `doctor`, because starting Docker's VM costs real memory. It says it is starting, shows progress, waits up to a stated timeout and reports clearly if the engine did not come up. It never runs `sudo`, printing the command instead, and never stops the engine, only its own labeled stacks. Install instructions are one short message per platform with a link to Docker's install page, kept in one place so the requirements summary, `doctor` and the Web UI's Start match. The start mechanism per platform is verified at implementation ([spec](../specs/service-projects.md#docker-states)) | Start the engine at `doctor` or whenever a problem is shown | Earlier and less waiting at Start, at the cost of a VM's memory for someone who is only reading |

Raised while drafting, for the same confirmation:

| # | Recommendation | Alternative | Trade-off |
|---|----------------|-------------|-----------|
| R18 | `cstudy test` on a service project runs `commands.test`, then the visible HTTP cases of the unlocked levels as feedback. No native test file is generated | Generated tests per language, as ADR 0014 does | Generation is per-language work in every phase, which the single grader exists to avoid. The cost: opening a level writes no test file, and the visible cases are not native tests you can debug |
| R19 | A migration that fails in `cstudy submit` is reported as an install failure is, with its output, and otherwise as code that does not load: the submission is stored and exits 2. A failed `install` exits 4 and stores nothing | Exit 4 for both | Your migration is your code, so storing it matches ADR 0014's rule; exit 4 would call your bug an environment problem |
| R20 | A first level asks for one small change as well as orientation, so the starter does not pass it untouched | A level the starter already passes | `cstudy done` takes a rating once level 1 passes, so a free pass would weaken it |
| R21 | `.env.local` is listed and editable but outside `code_hash` and archives, since archives are tracked and it may hold secrets; `--fresh` carries it to the new folder | Treat it as an ordinary file | An ordinary file would commit your settings through `.archive/` |

## Phases

| Phase | Scope |
|-------|-------|
| P1 | The lifecycle commands and their contract; dependency install and lock rules; the TypeScript and Python service templates; runtime files; `project.requires` with its static check and the dependency list in `cstudy show`, `cstudy list` and `cstudy start` |
| P2 | The Python mock server, `schemas/mock.schema.json`, its lifecycle, `cstudy dev` and the runtime `.env` |
| P3 | The HTTP grader, with `verify` and CI wired in. CI installs from the network, so it caches the pnpm store and the uv cache by lock digest |
| P4 | The first problem in TypeScript |
| P5 | The Python version of the first problem |
| P6 | Web UI: mock server status, the scenario picker, and the dependency list in the Problems view, the Problem view and the Start dialog |
| P7 | Docker services spike: `up --wait` time and memory with Postgres, Redis and LocalStack on macOS and Linux; the compose behaviors of R6; labels on everything compose creates; whether macOS CI runners have Docker. If the spike fails, the owner is told before anything is built |
| P8 | Docker services: `project.services`, the compose lifecycle, labels, sweep, doctor rows, image pull, a separate CI job |
| P9 | Data-driven problems, TypeScript then Python, each choosing its own database and migration tool. A problem may use SQLite with no Docker, so one can precede P8. Proves the flow of R8, with parallel cases and any contract table |
| P10 | Kotlin and Java templates and problems. Settles Gradle's `--offline` for these problems |
| P11 | Go template and problems. Settles `GOPROXY=off` and vendored modules for these problems |
| P12 | Rust template and problems (maybe; decided when reached). Settles vendored crates for these problems |
| Later | Running your app in a container, with mock servers reachable from it |

Each phase gets its docs and, at release, a website message. This plan runs after the code intelligence releases of [ADR 0018's Phases](0018-editor-code-intelligence.md#phases) (1 Python and TypeScript, 2 Java and Kotlin, 3 Go and Rust) unless the owner reorders it. The two share a language order only loosely: ADR 0018 puts Python and TypeScript in one release, and O7 here puts TypeScript first.

## Consequences

- NFR-6 now says what the owner meant, and the PRD's "no network at runtime" is qualified by it. A service project installs dependencies and pulls images at start. Everything else about NFR-6 is unchanged.
- Service projects cannot meet NFR-1's project targets: an app start plus real waits for `Retry-After` and delays take seconds, not 1.0 s. NFR-1 gains a target of its own once P3 measures it. As for D6, D7 and D10 in [ADR 0017](0017-async-project-problems.md), the new checks stay outside NFR-3's 30 s per problem.
- A service case runs on the real clock, against ADR 0017's "virtual time wherever code waits". `project.clock: virtual` is refused with `grading: http`, and a static limit plus a determinism check keep real waits short and stable.
- New surface, all planned: `project.grading`, `commands`, `app`, `mocks`, `services`, `requires`; `schemas/mock.schema.json`; HTTP and parallel case shapes in `tests.json`; `cstudy dev`; `cstudy start --yes`; `cstudy list --needs`; `origin: "runtime"`; checks S19 to S23 and D11; `docker` and `docker leftovers` doctor rows.
- The schema changes at implementation: `signature` and `project.entry` become conditional, and `project` gains the fields above. Until then `schemas/meta.schema.json` stays as it is.
- `is_untracked` becomes aware of the kind of project, because a service project's `uv.lock` is a file grading trusts, while a bank project's is tool output. The workspace `.gitignore` gains `projects/*/.env` and `projects/*/.env.local`, and a service starter's own `.gitignore` re-includes its lock file.
- `cstudy start` writes no `.venv` link for a service project, and `doctor --fix` restores none, since its `.venv` is a real directory. The risk ADR 0014 guarded against, `uv run` deleting the shared venv through the link, does not apply there.
- Disk grows per project (`node_modules`, `.venv`), and `cstudy start --fresh` already removes those through `remove_untracked`. There is no `cstudy reset` and no remove command ([Cleanup](../specs/service-projects.md#cleanup)).
- A dev stack and a graded stack can overlap for the length of a run. Declared memory limits bound each, and the spike measures the total.
- Reference solutions and hidden data stay hidden from language servers for catalog problems, because they stay in the content root. Your own problems under `<workspace>/problems/` are not one of the four hidden directories today, for references or for this ([Language servers](../specs/service-projects.md#language-servers)).
- `docs/README.md` indexes ADRs and `docs/architecture.md` describes adapters. Both change when the first phase lands.

## Revisit

| Trigger | What to reconsider |
|---------|--------------------|
| The P7 spike fails, or Docker's memory cost proves too high on an 18 GB machine | Report to the owner before building. The fallback is the owner's call |
| A hand-written `commands.test` proves too costly to author, or learners miss native tests per level | Generated tests per language, from the visible cases |
| The `grade_setup` flow cannot work with a problem's chosen migration tool | That problem's tool, or a contract table |
| A problem needs a stateful mock server, or path templates | Extending the mock config, which is deliberately stateless |
| Authors want your app in a container | The later phase, with mock servers in the compose network |
| A problem needs a parallel case's expected count to vary | A checker over the responses |
| Real waits push a submission past what is tolerable | Lower limits, or running your app on a controllable clock where the language allows |

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| A cstudy-managed native Postgres, from prebuilt binaries | Rejected by the owner: cstudy should not run a Postgres server directly on your machine, and Docker unlocks many services, such as Postgres, LocalStack and Redis, where a native approach would solve only one |
| Mock servers in the language of each problem | Rejected by O3: one written per language multiplies the work and the behaviors to keep equal |
| A third-party mock server tool | A dependency cstudy would have to install and pin, with scenario rules of its own |
| Scenario choice as a query parameter of the mocked API | It would leak into the vendor's contract, so code could read or fake it |
| Mock servers started by `cstudy start` | `cstudy start` exits, so they would be unowned daemons |
| A per-language dependency table in the core | A new language would need core code; templates hold the same decisions |
| Tool-specific fields such as `migrations: liquibase` | Rejected by O9: the core has no knowledge of any migration tool |
| Grading through the native test framework | The second judge that ADR 0010 and ADR 0014 rejected: editable code would give the verdict |
