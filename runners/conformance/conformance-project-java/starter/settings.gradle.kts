// This project's own Gradle build; open this folder in your IDE as a Gradle project.
// It finds the coding-study workspace by walking up to .cs/workspace.toml and builds with the
// workspace's version catalog and runner runtime, so keep this file as it is.
pluginManagement {
    var directory: File? = settingsDir
    while (directory != null && !directory.resolve(".cs/workspace.toml").isFile) {
        directory = directory.parentFile
    }
    val workspace = directory
        ?: throw GradleException("$settingsDir is not inside a coding-study workspace")
    extra["cs.workspace"] = workspace
    includeBuild(workspace.resolve(".cs/runtime/runners/jvm"))
}

val workspace = extra["cs.workspace"] as File

dependencyResolutionManagement {
    repositories {
        mavenCentral()
    }
    versionCatalogs {
        create("libs") {
            from(files(workspace.resolve("jvm/gradle/libs.versions.toml")))
        }
    }
}

rootProject.name = "conformance-project-java"

includeBuild(workspace.resolve(".cs/runtime/runners/jvm"))
