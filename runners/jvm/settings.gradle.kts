// The JVM runner, the support classes and the `cs.practice` Gradle plugin. Never built on its
// own: a workspace's jvm/ (and its reference build in .cs/build/jvm) include the copy in
// .cs/runtime with includeBuild.
rootProject.name = "cs-jvm"

dependencyResolutionManagement {
    repositories {
        mavenCentral()
    }
}

include("support", "runner", "practice-plugin")
