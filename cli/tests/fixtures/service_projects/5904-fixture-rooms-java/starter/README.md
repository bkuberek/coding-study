# Rooms in Java

`cstudy` runs this service in a Docker sandbox: your app sees this folder and nothing above it, and has no network beyond its stack.

- Run it and its tests: `cstudy test`. `scripts/run.sh` builds it with Gradle, offline, then starts it.
- It reads `PORT` and listens on all interfaces inside the container. `/health` answers 2xx once it is ready.
- `.env` lists the variables it reads.
