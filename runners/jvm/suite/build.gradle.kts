// cs.suite: hosts the JUnit Platform for project suite jobs; only on a project's test runtime
// classpath (docs/specs/runners.md#suite-job), where `cs.project` puts it.
plugins {
    java
}

group = "cs"

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(21)
    }
}

dependencies {
    implementation(project(":runner"))
    implementation(platform(libs.junit.bom))
    implementation(libs.junit.platform.launcher)
}
