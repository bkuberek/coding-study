// cs.support: ListNode, TreeNode and GraphNode, on the compile classpath of user code.
plugins {
    `java-library`
}

group = "cs"

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(21)
    }
}
