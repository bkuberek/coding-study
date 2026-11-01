// The JVM runner, the support classes, the JUnit Platform host for project suites, and the
// `cs.practice` and `cs.project` Gradle plugins. Never built on its own: a workspace's jvm/, its
// reference build in .cs/build/jvm and every project folder include the copy in .cs/runtime with
// includeBuild.
rootProject.name = "cs-jvm"

dependencyResolutionManagement {
    repositories {
        mavenCentral()
        // The Kotlin Gradle plugin's API, which the plugins compile against. A workspace that has
        // built Kotlin cached it with the Kotlin plugin from the plugin repository, and an offline
        // build finds a cached module only through the repository that cached it.
        gradlePluginPortal()
    }
}

include("support", "runner", "suite", "practice-plugin")
