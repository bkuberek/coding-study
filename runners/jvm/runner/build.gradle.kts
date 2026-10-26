// cs.runner.Main: speaks the runner protocol (docs/specs/runners.md); on the runtime classpath only.
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
    implementation(project(":support"))
    implementation(libs.gson)
}
