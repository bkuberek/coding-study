# {{title}}

`cstudy` runs this service in a Docker sandbox: your app sees this folder and nothing above it, and has no network beyond its stack.

- Run it and its tests: `cstudy test`. `scripts/run.sh` builds the app with `go build`, with no network, then starts it; the tests are `go test`'s, in `*_test.go`.
- It reads `PORT` and listens on all interfaces inside the container. `/health` answers 2xx once it is ready.
- `.env` lists the variables it reads. Go comes with the image, so your machine needs none.
- `go.sum` is the lock: the checksum of every module the build needs, empty while it needs only the standard library. To add a module, import it, then write the lock: `cstudy dev --exec --network -- env GOPROXY=https://proxy.golang.org go mod tidy`. The next command installs it.
