// cs.suite: hosts the JUnit Platform for project suite jobs; only on a project's test runtime
// classpath (docs/specs/runners.md#suite-job), where `cs.project` puts it.
plugins {
    java
}

group = "cs"

// No toolchain: compiled by the JDK the build runs on, at the oldest supported release, so the
// classes load on every JDK cstudy runs on (docs/specs/runners.md#the-jdk-and-the-release-level).
tasks.withType<JavaCompile>().configureEach {
    options.release = libs.versions.jdk.minimum.get().toInt()
}

dependencies {
    implementation(project(":runner"))
    implementation(platform(libs.junit.bom))
    implementation(libs.junit.platform.launcher)
}
