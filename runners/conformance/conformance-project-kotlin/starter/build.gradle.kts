// Builds with the workspace's JDK, Kotlin, kotlin.test on JUnit 5 and the cstudy runner (the
// cs.project plugin); keep this file as it is.
plugins {
    alias(libs.plugins.kotlin.jvm)
    id("cs.project")
}
