// cs.support: ListNode, TreeNode and GraphNode, on the compile classpath of user code.
plugins {
    `java-library`
}

group = "cs"

// No toolchain: compiled by the JDK the build runs on, at the oldest supported release, so the
// classes load on every JDK cstudy runs on (docs/specs/runners.md#the-jdk-and-the-release-level).
tasks.withType<JavaCompile>().configureEach {
    options.release = libs.versions.jdk.minimum.get().toInt()
}
