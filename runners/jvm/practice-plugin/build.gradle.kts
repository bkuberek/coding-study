// The `cs.practice` plugin applied by a workspace's jvm/java and jvm/kotlin projects, and the
// `cs.project` plugin applied by a Java or Kotlin project problem's folder.
plugins {
    `java-gradle-plugin`
}

group = "cs"

// No toolchain: compiled by the JDK the build runs on, at the oldest supported release, so the
// plugins load on every JDK cstudy runs on (docs/specs/runners.md#the-jdk-and-the-release-level).
tasks.withType<JavaCompile>().configureEach {
    options.release = libs.versions.jdk.minimum.get().toInt()
}

dependencies {
    // Only to set the release level of Kotlin compiles; a Kotlin project brings the plugin itself.
    compileOnly(libs.kotlin.gradle.plugin.api)
}

// The supported JDK range of the version catalog, as a resource the plugins read.
val jdkRange = tasks.register<WriteProperties>("jdkRange") {
    description = "Writes the supported JDK range for the plugins."
    destinationFile = layout.buildDirectory.file("generated/jdk-range/cs/gradle/jdk-range.properties")
    property("minimum", libs.versions.jdk.minimum.get())
    property("maximum", libs.versions.jdk.maximum.get())
}

sourceSets.main {
    resources.srcDir(files(layout.buildDirectory.dir("generated/jdk-range")).builtBy(jdkRange))
}

gradlePlugin {
    plugins {
        create("practice") {
            id = "cs.practice"
            implementationClass = "cs.gradle.PracticePlugin"
        }
        create("project") {
            id = "cs.project"
            implementationClass = "cs.gradle.ProjectPlugin"
        }
    }
}
