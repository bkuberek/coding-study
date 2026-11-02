// cs.coroutines: the runner's bridge to the kotlinx-coroutines-test scheduler, on the main runtime
// classpath of a Kotlin project that applies the `cs.coroutines` plugin
// (docs/specs/runners.md#virtual-clock-and-stress-in-project-jobs).
import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    alias(libs.plugins.kotlin.jvm)
}

group = "cs"

// No toolchain: compiled by the JDK the build runs on, at the oldest supported release, so the
// classes load on every JDK cstudy runs on (docs/specs/runners.md#the-jdk-and-the-release-level).
val release = libs.versions.jdk.minimum.get()

tasks.withType<JavaCompile>().configureEach {
    options.release = release.toInt()
}

kotlin {
    compilerOptions {
        jvmTarget = JvmTarget.fromTarget(release)
        freeCompilerArgs.add("-Xjdk-release=$release")
    }
}

dependencies {
    implementation(project(":runner"))
    implementation(libs.kotlinx.coroutines.core)
    implementation(libs.kotlinx.coroutines.test)
}
