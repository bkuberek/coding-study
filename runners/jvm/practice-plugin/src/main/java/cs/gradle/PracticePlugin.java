package cs.gradle;

import java.util.regex.Pattern;
import org.gradle.api.GradleException;
import org.gradle.api.Plugin;
import org.gradle.api.Project;
import org.gradle.api.file.SourceDirectorySet;
import org.gradle.api.plugins.JavaPlugin;
import org.gradle.api.plugins.JavaPluginExtension;
import org.gradle.api.provider.Provider;
import org.gradle.api.tasks.SourceSet;
import org.gradle.jvm.toolchain.JavaLanguageVersion;

/**
 * Configures a Java or Kotlin practice project (docs/specs/runners.md#jvm-build-details).
 *
 * <ul>
 *   <li>JVM toolchain 21; {@code cs.support} on the compile classpath and {@code cs.runner} on the
 *       runtime classpath, both from the included build {@code runners/jvm}.
 *   <li>{@code -Pcs.only=<snake_slug>} restricts the main source set to that problem's package
 *       ({@code practice/<snake_slug>} or {@code ref/<snake_slug>}), so a broken file for another
 *       problem never blocks this one. IDEs build without it and see everything.
 *   <li>{@code csClasspath} writes the runtime classpath to {@code build/cs/runtime-classpath.txt}.
 * </ul>
 */
public class PracticePlugin implements Plugin<Project> {
    static final String ONLY_PROPERTY = "cs.only";
    static final String CLASSPATH_TASK = "csClasspath";
    static final String CLASSPATH_FILE = "cs/runtime-classpath.txt";
    private static final int JAVA_VERSION = 21;
    private static final String KOTLIN_PLUGIN = "org.jetbrains.kotlin.jvm";
    private static final String KOTLIN_SOURCES = "kotlin";
    private static final Pattern SNAKE_SLUG = Pattern.compile("[a-z][a-z0-9_]*");
    private static final String[] PACKAGE_ROOTS = {"practice", "ref"};

    @Override
    public void apply(Project project) {
        project.getPluginManager().apply(JavaPlugin.class);
        JavaPluginExtension java = project.getExtensions().getByType(JavaPluginExtension.class);
        java.getToolchain().getLanguageVersion().set(JavaLanguageVersion.of(JAVA_VERSION));
        SourceSet main = java.getSourceSets().getByName(SourceSet.MAIN_SOURCE_SET_NAME);
        restrictToOneProblem(project, main);
        project.getDependencies().add(JavaPlugin.IMPLEMENTATION_CONFIGURATION_NAME, "cs:support");
        project.getDependencies().add(JavaPlugin.RUNTIME_ONLY_CONFIGURATION_NAME, "cs:runner");
        project.getTasks().register(CLASSPATH_TASK, WriteClasspath.class, task -> {
            task.setDescription("Writes the runtime classpath for cs.runner.Main.");
            task.getClasspath().from(main.getRuntimeClasspath());
            task.getOutputFile().set(project.getLayout().getBuildDirectory().file(CLASSPATH_FILE));
        });
    }

    private static void restrictToOneProblem(Project project, SourceSet main) {
        Provider<String> only = project.getProviders().gradleProperty(ONLY_PROPERTY);
        if (!only.isPresent()) {
            return;
        }
        // Includes on the source set itself; its filter already includes every *.java or *.kt
        // file, and includes within one pattern set match when any of them does.
        String[] patterns = problemPatterns(only.get());
        main.getJava().include(patterns);
        project.getPluginManager().withPlugin(KOTLIN_PLUGIN, applied -> {
            SourceDirectorySet kotlin =
                    (SourceDirectorySet) main.getExtensions().getByName(KOTLIN_SOURCES);
            kotlin.include(patterns);
        });
    }

    private static String[] problemPatterns(String snakeSlug) {
        if (!SNAKE_SLUG.matcher(snakeSlug).matches()) {
            throw new GradleException(ONLY_PROPERTY + " must be a snake_slug, not " + snakeSlug);
        }
        String[] patterns = new String[PACKAGE_ROOTS.length];
        for (int index = 0; index < PACKAGE_ROOTS.length; index++) {
            patterns[index] = PACKAGE_ROOTS[index] + "/" + snakeSlug + "/**";
        }
        return patterns;
    }
}
