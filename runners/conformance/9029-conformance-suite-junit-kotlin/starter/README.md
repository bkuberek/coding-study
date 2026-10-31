# Probe

A project for the runner conformance suite: `src/main/kotlin/probe/Probe.kt` defines the entry class `probe.Probe`, and the reference adds `src/test/kotlin/probe/StatusesTest.kt`, whose tests cover every status of a suite job, and `BrokenSetupTest.kt`, whose setup fails.

`cstudy` loads `probe.Probe`. Run the tests with `../../jvm/gradlew test`.
