// The app's build. Gradle comes with the project's image, and cstudy runs it in the sandbox:
// `commands.install` once with the network, every other command offline from what it downloaded.
import org.gradle.api.tasks.testing.logging.TestExceptionFormat
import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    kotlin("jvm") version "2.4.21"
    kotlin("plugin.serialization") version "2.4.21"
    application
}

repositories {
    mavenCentral()
}

dependencies {
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.12.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.11.0")
    testImplementation(kotlin("test"))
}

kotlin {
    compilerOptions {
        jvmTarget = JvmTarget.JVM_25
    }
}

tasks.withType<JavaCompile>().configureEach {
    options.release = 25
}

application {
    mainClass = "coworking.MainKt"
    applicationName = "app"
    applicationDefaultJvmArgs = listOf("-Xmx128m", "-XX:+UseSerialGC")
}

tasks.test {
    useJUnitPlatform()
    maxHeapSize = "128m"
    testLogging {
        events("passed", "skipped", "failed")
        exceptionFormat = TestExceptionFormat.FULL
    }
}

// What `commands.install` runs: it resolves every file that compiling, testing and installing the
// app read, the Kotlin compiler's own among them, without running them, so each later build finds
// them offline. After you change a dependency, write the lock from it, asking the repository again
// so nothing is left out:
// cstudy dev --exec --network -- gradle --refresh-dependencies
//   --write-verification-metadata sha256 resolveDependencies
tasks.register("resolveDependencies") {
    val read = listOf("compileKotlin", "compileTestKotlin", "test", "installDist").map {
        tasks.named(it).get().inputs.files
    }
    doLast { read.forEach { it.files } }
}
