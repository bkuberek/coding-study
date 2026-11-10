# Coworking Availability

A coworking space sells hot desks it counts itself and meeting rooms from outside vendors. This is the start of the one API that says what can be booked on a day.

`cstudy` runs this service in a Docker sandbox: your app sees this folder and nothing above it, and has no network beyond its stack.

## Running it

| Command | What it does |
|---------|--------------|
| `cstudy dev` | Runs your app with its vendors, in the foreground, and prints its URL. Ctrl-C stops it |
| `cstudy dev --scenario room-vendor=outage` | The same, with a vendor misbehaving, by a name from its `API.md` |
| `cstudy test` | Runs your kotlin.test tests beside the app, then the visible cases of your open levels |
| `cstudy submit` | Grades every case of your open levels, and opens the next level when they pass |

Your app reads `PORT` and listens on all interfaces inside the container. `/health` answers 200 once it is ready. `scripts/run.sh` builds it with Gradle, with no network, then starts it.

## Layout

| Path | Holds |
|------|-------|
| `src/main/kotlin/coworking/Main.kt` | The routes, and where the server starts |
| `src/main/kotlin/coworking/DeskInventory.kt` | The daily counts |
| `src/main/kotlin/coworking/Query.kt` | `URI.queryValue`: the value of a query parameter |
| `data/desks.json` | The seeded counts, per day |
| `src/test/kotlin/coworking/` | Your tests, with two helpers: `App` asks your app, and `Vendors.setScenario` sets a vendor's visible scenario |
| `vendors/<name>/API.md` | Each vendor's contract, for reading |
| `.env` | What your app reads, written by `cstudy start`. Its environment already holds it |

It is a Gradle build of Kotlin 2.4 on JDK 25, with kotlinx.serialization for JSON, kotlinx.coroutines, and kotlin.test on JUnit 5 for the tests; Gradle and the JDK come with the sandbox's image. `gradle/verification-metadata.xml` is the lock: the checksum of every artifact the install downloads. To add a dependency, add it to `build.gradle.kts`, then write the lock: `cstudy dev --exec --network -- gradle --refresh-dependencies --write-verification-metadata sha256 resolveDependencies`. The next command installs it.
