# {{title}}

`cstudy` runs this service in a Docker sandbox: your app sees this folder and nothing above it, and has no network beyond its stack.

- Run it and its tests: `cstudy test`
- It reads `PORT` and listens on all interfaces inside the container (`0.0.0.0`). `/health` answers 2xx once it is ready.
- `.env` lists the variables it reads. The lock file is what the install uses, exactly; add a dependency from a shell of your own and commit the lock with it.
