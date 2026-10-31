// The JVM runner, the support classes, the JUnit Platform host for project suites, and the
// `cs.practice` and `cs.project` Gradle plugins. Never built on its own: a workspace's jvm/, its
// reference build in .cs/build/jvm and every project folder include the copy in .cs/runtime with
// includeBuild.
rootProject.name = "cs-jvm"

dependencyResolutionManagement {
    repositories {
        mavenCentral()
    }
}

include("support", "runner", "suite", "practice-plugin")
