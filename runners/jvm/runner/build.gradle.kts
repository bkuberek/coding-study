// cs.runner.Main: speaks the runner protocol (docs/specs/runners.md); on the runtime classpath only.
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
    implementation(project(":support"))
    implementation(libs.gson)
}
