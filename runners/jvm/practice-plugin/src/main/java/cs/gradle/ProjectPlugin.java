package cs.gradle;

import java.util.ArrayList;
import java.util.List;
import org.gradle.api.Plugin;
import org.gradle.api.Project;
import org.gradle.api.artifacts.dsl.DependencyHandler;
import org.gradle.api.file.SourceDirectorySet;
import org.gradle.api.plugins.JavaPlugin;
import org.gradle.api.plugins.JavaPluginExtension;
import org.gradle.api.provider.Provider;
import org.gradle.api.tasks.SourceSet;
import org.gradle.api.tasks.TaskProvider;
import org.gradle.api.tasks.testing.Test;
import org.gradle.jvm.toolchain.JavaLanguageVersion;

/**
 * Configures a Java or Kotlin project problem's folder (docs/specs/runners.md#project-jobs).
 *
 * <ul>
 *   <li>JVM toolchain 21; JUnit Jupiter for the tests, and kotlin.test on JUnit 5 with Kotlin;
 *       {@code cs.runner} on the runtime classpath and its JUnit Platform host {@code cs.suite}
 *       on the test runtime classpath, both from the included build {@code runners/jvm}.
 *   <li>{@code -Pcs.exclude=<path>,...} leaves those test files, relative to the project, out of
 *       the test compile: the generated tests of levels above {@code cstudy test --level}, which
 *       may call methods that do not exist yet. IDEs build without it and see everything.
 *   <li>{@code csMainClasspath} writes the main runtime classpath to
 *       {@code build/cs/main-classpath.txt} (grading); {@code csClasspath} writes it and the test
 *       runtime classpath to {@code build/cs/test-classpath.txt} (the suite).
 * </ul>
 */
public class ProjectPlugin implements Plugin<Project> {
    static final String EXCLUDE_PROPERTY = "cs.exclude";
    static final String CLASSPATH_TASK = "csClasspath";
    static final String MAIN_CLASSPATH_TASK = "csMainClasspath";
    static final String MAIN_CLASSPATH_FILE = "cs/main-classpath.txt";
    static final String TEST_CLASSPATH_FILE = "cs/test-classpath.txt";
    /** The JUnit release of the runners' version catalog, whose launcher {@code cs.suite} uses. */
    static final String JUNIT_VERSION = "5.14.4";
    private static final int JAVA_VERSION = 21;
    private static final String KOTLIN_PLUGIN = "org.jetbrains.kotlin.jvm";
    private static final String KOTLIN_SOURCES = "kotlin";
    private static final String[] TEST_SOURCE_ROOTS = {"src/test/java/", "src/test/kotlin/"};
    private static final String PATH_SEPARATOR = ",";

    @Override
    public void apply(Project project) {
        project.getPluginManager().apply(JavaPlugin.class);
        JavaPluginExtension java = project.getExtensions().getByType(JavaPluginExtension.class);
        java.getToolchain().getLanguageVersion().set(JavaLanguageVersion.of(JAVA_VERSION));
        SourceSet main = java.getSourceSets().getByName(SourceSet.MAIN_SOURCE_SET_NAME);
        SourceSet test = java.getSourceSets().getByName(SourceSet.TEST_SOURCE_SET_NAME);
        excludeTestFiles(project, test);
        addDependencies(project);
        project.getTasks().named(JavaPlugin.TEST_TASK_NAME, Test.class, Test::useJUnitPlatform);
        TaskProvider<WriteClasspath> mainClasspath = project.getTasks().register(
                MAIN_CLASSPATH_TASK, WriteClasspath.class, task -> {
                    task.setDescription("Writes the main runtime classpath for grading.");
                    task.getClasspath().from(main.getRuntimeClasspath());
                    task.getOutputFile().set(
                            project.getLayout().getBuildDirectory().file(MAIN_CLASSPATH_FILE));
                });
        project.getTasks().register(CLASSPATH_TASK, WriteClasspath.class, task -> {
            task.setDescription("Writes the main and test runtime classpaths for the suite.");
            task.dependsOn(mainClasspath);
            task.getClasspath().from(test.getRuntimeClasspath());
            task.getOutputFile().set(
                    project.getLayout().getBuildDirectory().file(TEST_CLASSPATH_FILE));
        });
    }

    private static void addDependencies(Project project) {
        DependencyHandler dependencies = project.getDependencies();
        String testImplementation = JavaPlugin.TEST_IMPLEMENTATION_CONFIGURATION_NAME;
        dependencies.add(
                testImplementation, dependencies.platform("org.junit:junit-bom:" + JUNIT_VERSION));
        dependencies.add(testImplementation, "org.junit.jupiter:junit-jupiter");
        dependencies.add(JavaPlugin.RUNTIME_ONLY_CONFIGURATION_NAME, "cs:runner");
        dependencies.add(JavaPlugin.TEST_RUNTIME_ONLY_CONFIGURATION_NAME, "cs:suite");
        project.getPluginManager().withPlugin(KOTLIN_PLUGIN, applied ->
                dependencies.add(testImplementation, "org.jetbrains.kotlin:kotlin-test"));
    }

    private static void excludeTestFiles(Project project, SourceSet test) {
        Provider<String> excluded = project.getProviders().gradleProperty(EXCLUDE_PROPERTY);
        if (!excluded.isPresent()) {
            return;
        }
        String[] patterns = sourcePatterns(excluded.get());
        test.getJava().exclude(patterns);
        project.getPluginManager().withPlugin(KOTLIN_PLUGIN, applied -> {
            SourceDirectorySet kotlin =
                    (SourceDirectorySet) test.getExtensions().getByName(KOTLIN_SOURCES);
            kotlin.exclude(patterns);
        });
    }

    /** {@code src/test/java/bank/Level2Test.java} as {@code bank/Level2Test.java}, the pattern
     * of that file below its source directory. */
    private static String[] sourcePatterns(String paths) {
        List<String> patterns = new ArrayList<>();
        for (String path : paths.split(PATH_SEPARATOR)) {
            for (String root : TEST_SOURCE_ROOTS) {
                if (path.startsWith(root)) {
                    patterns.add(path.substring(root.length()));
                }
            }
        }
        return patterns.toArray(String[]::new);
    }
}
