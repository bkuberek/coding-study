// The `cs.practice` plugin applied by a workspace's jvm/java and jvm/kotlin projects.
plugins {
    `java-gradle-plugin`
}

group = "cs"

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(21)
    }
}

gradlePlugin {
    plugins {
        create("practice") {
            id = "cs.practice"
            implementationClass = "cs.gradle.PracticePlugin"
        }
    }
}
