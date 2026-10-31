// The `cs.practice` plugin applied by a workspace's jvm/java and jvm/kotlin projects, and the
// `cs.project` plugin applied by a Java or Kotlin project problem's folder.
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
        create("project") {
            id = "cs.project"
            implementationClass = "cs.gradle.ProjectPlugin"
        }
    }
}
