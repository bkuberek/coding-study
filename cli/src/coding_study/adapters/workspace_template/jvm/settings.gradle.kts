// Java and Kotlin practice projects; open this directory in IntelliJ as one Gradle project.
// `cstudy test` builds one problem with `./gradlew :<lang>:csClasspath -Pcs.only=<snake_slug>`.
// The runner and the `cs.practice` plugin come from ../.cs/runtime (`cstudy doctor --fix` recreates it).
pluginManagement {
    includeBuild("../.cs/runtime/runners/jvm")
}

dependencyResolutionManagement {
    repositories {
        mavenCentral()
    }
}

rootProject.name = "coding-study-jvm"

includeBuild("../.cs/runtime/runners/jvm")
include("java", "kotlin")
