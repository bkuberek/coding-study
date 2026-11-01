package cs.gradle;

import org.gradle.api.Project;
import org.jetbrains.kotlin.gradle.dsl.JvmTarget;
import org.jetbrains.kotlin.gradle.dsl.KotlinJvmCompilerOptions;
import org.jetbrains.kotlin.gradle.tasks.KotlinJvmCompile;

/**
 * The release level of a build's Kotlin compiles. The only class of the plugins that names a type
 * of the Kotlin Gradle plugin, which they compile against but do not bring: it is loaded only in a
 * project that applies that plugin.
 */
final class KotlinRelease {
    private static final String JDK_RELEASE_FLAG = "-Xjdk-release=";

    private KotlinRelease() {}

    static void apply(Project project, int level) {
        JvmTarget target = JvmTarget.Companion.fromTarget(String.valueOf(level));
        project.getTasks().withType(KotlinJvmCompile.class).configureEach(task -> {
            KotlinJvmCompilerOptions options = task.getCompilerOptions();
            options.getJvmTarget().set(target);
            options.getFreeCompilerArgs().add(JDK_RELEASE_FLAG + level);
        });
    }
}
