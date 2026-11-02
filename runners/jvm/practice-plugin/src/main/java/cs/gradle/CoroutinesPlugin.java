package cs.gradle;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.util.Properties;
import org.gradle.api.GradleException;
import org.gradle.api.Plugin;
import org.gradle.api.Project;
import org.gradle.api.artifacts.dsl.DependencyHandler;
import org.gradle.api.plugins.JavaPlugin;

/**
 * Puts a Kotlin project problem on the virtual clock (docs/specs/runners.md#virtual-clock-and-
 * stress-in-project-jobs), beside {@code cs.project}.
 *
 * <ul>
 *   <li>{@code kotlinx-coroutines-core} and {@code kotlinx-coroutines-test} on the main and test
 *       classpaths, at the release of the runners' version catalog: the code suspends and reads
 *       the test scheduler's time, and the tests run on {@code runTest}.
 *   <li>{@code cs.coroutines}, the runner's bridge to the test scheduler, on the main runtime
 *       classpath, where {@code cs.runner.Main} finds it.
 * </ul>
 *
 * <p>Only Kotlin clock projects apply it, so no other build resolves the coroutine libraries;
 * the Kotlin warm-up project of {@code cstudy doctor --fix} applies it, which caches them for
 * offline builds.
 */
public class CoroutinesPlugin implements Plugin<Project> {
    static final String VERSIONS_RESOURCE = "coroutines.properties";
    private static final String GROUP = "org.jetbrains.kotlinx:";
    private static final String[] LIBRARIES = {"kotlinx-coroutines-core", "kotlinx-coroutines-test"};

    @Override
    public void apply(Project project) {
        project.getPluginManager().apply(JavaPlugin.class);
        DependencyHandler dependencies = project.getDependencies();
        String version = version();
        for (String library : LIBRARIES) {
            dependencies.add(
                    JavaPlugin.IMPLEMENTATION_CONFIGURATION_NAME, GROUP + library + ":" + version);
        }
        dependencies.add(JavaPlugin.RUNTIME_ONLY_CONFIGURATION_NAME, "cs:coroutines");
    }

    /** The coroutine libraries' release, from the runners' version catalog. */
    static String version() {
        Properties versions = new Properties();
        try (InputStream input = CoroutinesPlugin.class.getResourceAsStream(VERSIONS_RESOURCE)) {
            if (input == null) {
                throw new GradleException(VERSIONS_RESOURCE + " is missing from the cs plugins");
            }
            versions.load(input);
        } catch (IOException error) {
            throw new UncheckedIOException(error);
        }
        return versions.getProperty("kotlinx-coroutines");
    }
}
