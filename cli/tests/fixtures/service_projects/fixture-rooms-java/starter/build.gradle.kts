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
    mainClass = "rooms.Server"
    applicationName = "app"
    applicationDefaultJvmArgs = listOf("-Xmx128m", "-XX:+UseSerialGC")
}

tasks.test {
    useJUnitPlatform()
    maxHeapSize = "128m"
}

tasks.register("resolveDependencies") {
    val read = listOf("compileJava", "compileTestJava", "test", "installDist").map {
        tasks.named(it).get().inputs.files
    }
    doLast { read.forEach { it.files } }
}
