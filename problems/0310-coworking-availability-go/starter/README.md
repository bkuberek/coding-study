# Coworking Availability

A coworking space sells hot desks it counts itself and meeting rooms from outside vendors. This is the start of the one API that says what can be booked on a day.

`cstudy` runs this service in a Docker sandbox: your app sees this folder and nothing above it, and has no network beyond its stack.

## Running it

| Command | What it does |
|---------|--------------|
| `cstudy dev` | Runs your app with its vendors, in the foreground, and prints its URL. Ctrl-C stops it |
| `cstudy dev --scenario room-vendor=outage` | The same, with a vendor misbehaving, by a name from its `API.md` |
| `cstudy test` | Runs your `go test` tests beside the app, then the visible cases of your open levels |
| `cstudy submit` | Grades every case of your open levels, and opens the next level when they pass |

Your app reads `PORT` and listens on all interfaces inside the container. `/health` answers 200 once it is ready. `scripts/run.sh` builds it with `go build`, with no network, then starts it. The first build of the project also compiles the parts of Go's standard library it uses, so the first stack takes a minute or so; the next ones start in seconds.

## Layout

| Path | Holds |
|------|-------|
| `main.go` | Where the server starts |
| `server.go` | The routes |
| `desks.go` | The daily counts |
| `data/desks.json` | The seeded counts, per day |
| `*_test.go` | Your tests, with helpers in `helpers_test.go`: `serve` runs a handler for a test, `get` asks it, and `setScenario` sets a vendor's visible scenario |
| `vendors/<name>/API.md` | Each vendor's contract, for reading |
| `.env` | What your app reads, written by `cstudy start`. Its environment already holds it |

It is a Go module on the standard library alone: `net/http` serves the API and asks the vendors, and `encoding/json` reads and writes JSON. Go comes with the sandbox's image. `go.sum` is the lock, the checksum of every module the build needs, and empty while it needs none. To add a module, import it, then write the lock: `cstudy dev --exec --network -- env GOPROXY=https://proxy.golang.org go mod tidy`. The next command installs it.
