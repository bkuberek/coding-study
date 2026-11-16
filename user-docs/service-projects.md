---
title: Service projects and the dev stack
summary: Projects that run a real app in a Docker sandbox with mock servers, how they are tested and graded, and cstudy dev for your own IDE and debugger.
section: Practice
order: 70
---

# Service projects and the dev stack

A **service project** is a project problem whose code is a real app, such as a small web service. `cstudy` runs it in a sandbox on your own Docker, beside mock servers for the APIs it calls and, for some projects, a real database or other backing service. It is graded over HTTP, level by level, as a client would use it.

You need Docker, and nothing else: the project's image is its toolchain, so you need no Node.js or Python of your own for it. Every other problem runs without Docker and never asks it anything ([Docker](toolchains.md#docker)).

## Before you start

`cstudy show` and `cstudy start` list what a project needs before anything downloads: Docker, its images, the size of its install and the memory it takes. `cstudy list --needs none` keeps the problems that need nothing beyond a language's toolchain, and `cstudy list --needs docker` the ones that need Docker.

```bash
cstudy show llm-gateway-typescript
cstudy start llm-gateway-typescript    # asks before it downloads; --yes does not
```

`cstudy start` starts a stopped Docker engine, copies the starter files to `projects/<slug>/`, pulls the images and installs the dependencies in a container. It starts nothing else, and prints `cstudy dev` as the next step.

## Test and submit

| Command | Does |
|---------|------|
| `cstudy test` | Starts a test stack, runs the project's own tests, then the visible HTTP cases of the open levels. It is feedback: nothing is stored and nothing opens |
| `cstudy submit` | Starts a fresh stack and grades every case of every open level. A submission that passes them all opens the next level |
| `cstudy done` | Finishes the attempt, as for any project ([levels and projects](levels.md#when-you-finish)) |

The time the stack takes to start is reported apart, and never counts toward a time limit or a result. When a run ends or you stop it with `Ctrl+C`, `cstudy` takes the stack down.

## The dev stack

`cstudy dev` runs your app with its mock servers in the foreground, until `Ctrl+C`, so you can call it yourself:

```bash
cstudy dev
cstudy dev --scenario primary=outage   # start the mock server primary in its outage scenario
```

It prints your app's address on this computer, `http://127.0.0.1:<port>`, and one line per request a mock server receives. A **scenario** makes a mock server answer in a given way, such as slowly or with errors, so you can see how your app copes; a name `cstudy dev` does not know makes it list the ones you can use.

| You want | Run |
|----------|-----|
| Your app running, with its mock servers, until `Ctrl+C` | `cstudy dev` |
| Empty data | `cstudy dev --reset-data` |
| A dependency added | `cstudy dev --exec --network -- corepack pnpm add <package>`, or `cstudy dev --exec --network -- uv add <package>` for Python |
| One command in the app's environment | `cstudy dev --exec -- <command>` |

The dev stack keeps its data between runs, until `--reset-data`. The web UI starts the same stack from the Attempt view, with **Start dev stack**, and shows its stage, your app's address and its last lines ([the web UI](web-ui.md#service-projects-in-the-page)).

## Your own IDE and debugger

| You want | Run |
|----------|-----|
| VS Code or IntelliJ IDEA in a container of the project's image | `cstudy dev`, or `cstudy dev --no-run` to run the app from the IDE, then open the project folder's `.devcontainer/devcontainer.json`, which `cstudy dev` writes, in the IDE |
| A debugger attached to your app | `cstudy dev --debug`, then attach to the `debug` address it prints: Node's inspector for TypeScript, debugpy for Python, which the project must list as a dependency |

These flags stay in the terminal; the web UI's dev stack runs your app as `cstudy dev` does.

## The sandbox

`cstudy` limits only its own containers, and never changes a setting of your Docker engine or stops it. An install of dependencies can reach the network, so packages' install scripts stay off; a run has no way out at all. Your app reaches only its mock servers and backing services.

On Linux, `cstudy` never runs `sudo`. When it cannot start or reach Docker, it says what to run ([Docker](toolchains.md#docker)). `cstudy doctor` shows Docker as a `WARN` when it is missing, and `cstudy doctor --fix` removes what a project left behind, by its labels only.

## Code intelligence

With code intelligence on, the editor of the web UI checks a service project's code with a language server that runs in a sandboxed container of its own, with no network, and reads the packages the install put in the project. While Docker does not answer, the status bar says so with **Restart**, and the editor works without it ([the editor](editor.md)).
