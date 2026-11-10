# {{title}}

`cstudy` runs this service in a Docker sandbox: your app sees this folder and nothing above it, and has no network beyond its stack.

- Run it and its tests: `cstudy test`. `scripts/run.sh` builds the app with Gradle, offline, then starts it; the tests are kotlin.test on JUnit, under `src/test/kotlin`.
- It reads `PORT` and listens on all interfaces inside the container. `/health` answers 2xx once it is ready.
- `.env` lists the variables it reads. Gradle and JDK 25 come with the image, and Kotlin with the install, so your machine needs none of them.
- `gradle/verification-metadata.xml` is the lock: the checksum of every artifact the install downloads. To add a dependency, add it to `build.gradle.kts`, then write the lock: `cstudy dev --exec --network -- gradle --refresh-dependencies --write-verification-metadata sha256 resolveDependencies`. The next command installs it.
