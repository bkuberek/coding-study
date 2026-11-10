// The app's build. Gradle comes with the project's image, and cstudy runs it in the sandbox:
// `commands.install` once with the network, every other command offline from what it downloaded.
import org.gradle.api.tasks.testing.logging.TestExceptionFormat

plugins {
    application
}

repositories {
    mavenCentral()
}

dependencies {
    implementation("tools.jackson.core:jackson-databind:3.3.0")
    testImplementation(platform("org.junit:junit-bom:5.14.4"))
    testImplementation("org.junit.jupiter:junit-jupiter")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

tasks.withType<JavaCompile>().configureEach {
    options.release = 25
}

application {
    mainClass = "coworking.Server"
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
// app read, without running them, so each later build finds them offline. After you change a
// dependency, write the lock from it, asking the repository again so nothing is left out:
// cstudy dev --exec --network -- gradle --refresh-dependencies
//   --write-verification-metadata sha256 resolveDependencies
tasks.register("resolveDependencies") {
    val read = listOf("compileJava", "compileTestJava", "test", "installDist").map {
        tasks.named(it).get().inputs.files
    }
    doLast { read.forEach { it.files } }
}
