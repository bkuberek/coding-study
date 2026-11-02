// Builds with the workspace's JDK, Kotlin, kotlin.test on JUnit 5, kotlinx-coroutines and the
// cstudy runner (the cs.project and cs.coroutines plugins); keep this file as it is.
plugins {
    alias(libs.plugins.kotlin.jvm)
    id("cs.project")
    id("cs.coroutines")
}
