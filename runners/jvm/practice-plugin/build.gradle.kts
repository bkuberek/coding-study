// The `cs.practice` plugin applied by a workspace's jvm/java and jvm/kotlin projects, the
// `cs.project` plugin applied by a Java or Kotlin project problem's folder, and the
// `cs.coroutines` plugin applied by a Kotlin project problem on the virtual clock.
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

// The release of the coroutine libraries that `cs.coroutines` adds, from the version catalog.
val coroutinesVersion = tasks.register<WriteProperties>("coroutinesVersion") {
    description = "Writes the coroutine libraries' release for the cs.coroutines plugin."
    destinationFile =
        layout.buildDirectory.file("generated/coroutines/cs/gradle/coroutines.properties")
    property("kotlinx-coroutines", libs.versions.kotlinx.coroutines.get())
}

sourceSets.main {
    resources.srcDir(files(layout.buildDirectory.dir("generated/jdk-range")).builtBy(jdkRange))
    resources.srcDir(
        files(layout.buildDirectory.dir("generated/coroutines")).builtBy(coroutinesVersion)
    )
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
        create("coroutines") {
            id = "cs.coroutines"
            implementationClass = "cs.gradle.CoroutinesPlugin"
        }
    }
}
