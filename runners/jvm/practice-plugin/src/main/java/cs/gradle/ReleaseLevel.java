package cs.gradle;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.util.Properties;
import org.gradle.api.GradleException;
import org.gradle.api.Project;
import org.gradle.api.provider.Provider;
import org.gradle.api.tasks.compile.JavaCompile;

/**
 * The one release level of a build (docs/specs/runners.md#the-jdk-and-the-release-level).
 *
 * <p>No toolchain: everything compiles with the JDK the build runs on, the one cstudy selects.
 * The level is {@code -Pcs.release=<n>} when cstudy passes one (content compiles at the problem's
 * minimum), else the feature release of the build's JDK, capped at the newest supported release,
 * which the pinned Kotlin can still target. Every Java compile gets it as {@code options.release},
 * every Kotlin compile as {@code jvmTarget} and {@code -Xjdk-release}: Kotlin needs it set, or a
 * build on a JDK above the range fails on inconsistent targets.
 */
final class ReleaseLevel {
    static final String RELEASE_PROPERTY = "cs.release";
    private static final String RANGE_RESOURCE = "jdk-range.properties";
    private static final String KOTLIN_PLUGIN = "org.jetbrains.kotlin.jvm";

    private ReleaseLevel() {}

    static void apply(Project project) {
        int level = of(project);
        project.getTasks().withType(JavaCompile.class).configureEach(
                task -> task.getOptions().getRelease().set(level));
        // KotlinRelease is loaded only once the Kotlin plugin is applied: a Java project has
        // none of its types.
        project.getPluginManager().withPlugin(
                KOTLIN_PLUGIN, applied -> KotlinRelease.apply(project, level));
    }

    static int of(Project project) {
        int[] supported = supportedRange();
        Provider<String> release = project.getProviders().gradleProperty(RELEASE_PROPERTY);
        if (release.isPresent()) {
            return requested(release.get(), supported);
        }
        return Math.min(Runtime.version().feature(), supported[1]);
    }

    private static int requested(String text, int[] supported) {
        try {
            int level = Integer.parseInt(text.trim());
            if (level >= supported[0] && level <= supported[1]) {
                return level;
            }
        } catch (NumberFormatException ignored) {
            // reported below
        }
        throw new GradleException(RELEASE_PROPERTY + " must be a JDK release from " + supported[0]
                + " to " + supported[1] + ", not " + text);
    }

    /** The minimum and the maximum, from the runners' version catalog. */
    private static int[] supportedRange() {
        Properties range = new Properties();
        try (InputStream input = ReleaseLevel.class.getResourceAsStream(RANGE_RESOURCE)) {
            if (input == null) {
                throw new GradleException(RANGE_RESOURCE + " is missing from the cs plugins");
            }
            range.load(input);
        } catch (IOException error) {
            throw new UncheckedIOException(error);
        }
        return new int[] {
            Integer.parseInt(range.getProperty("minimum")),
            Integer.parseInt(range.getProperty("maximum"))
        };
    }
}
