package cs.suite;

import static org.junit.platform.engine.discovery.DiscoverySelectors.selectClasspathRoots;

import cs.runner.SuiteHost;
import cs.runner.SuiteListener;
import cs.runner.SuiteSelection;
import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import org.junit.platform.engine.FilterResult;
import org.junit.platform.engine.TestDescriptor;
import org.junit.platform.launcher.LauncherDiscoveryRequest;
import org.junit.platform.launcher.LauncherSession;
import org.junit.platform.launcher.PostDiscoveryFilter;
import org.junit.platform.launcher.core.LauncherDiscoveryRequestBuilder;
import org.junit.platform.launcher.core.LauncherFactory;

/**
 * Runs a project's JUnit Platform tests in the runner's process (docs/specs/runners.md#suite-job):
 * JUnit Jupiter for Java, and kotlin.test on JUnit 5 for Kotlin.
 *
 * <p>Tests are discovered in every directory of the classpath, the project's main and test class
 * directories, never in a jar, and run one at a time on the calling thread, so the runner sees
 * which test is in progress. A restart's {@code skip} leaves out a reported test, every test of a
 * reported class (a class whose setup failed, or a disabled one, is reported once under its own
 * id), and a parameterized or dynamic test with a reported invocation.
 */
public final class JUnitPlatformHost implements SuiteHost {
    static final String FRAMEWORK = "junit-platform";
    /** Explicit parameters outrank a project's junit-platform.properties. */
    private static final Map<String, String> CONFIGURATION =
            Map.of("junit.jupiter.execution.parallel.enabled", "false");

    @Override
    public String framework() {
        return FRAMEWORK;
    }

    @Override
    public void run(Path root, SuiteSelection selection, SuiteListener tests) {
        SourceFiles files = new SourceFiles(root);
        LauncherDiscoveryRequest request = LauncherDiscoveryRequestBuilder.request()
                .selectors(selectClasspathRoots(classDirectories()))
                .filters(new Selected(selection, files))
                .configurationParameters(CONFIGURATION)
                .build();
        try (LauncherSession session = LauncherFactory.openSession()) {
            session.getLauncher().execute(request, new Reporter(tests, files));
        }
    }

    private static Set<Path> classDirectories() {
        String classpath = System.getProperty("java.class.path", "");
        return Arrays.stream(classpath.split(File.pathSeparator))
                .map(Path::of)
                .filter(Files::isDirectory)
                .collect(Collectors.toCollection(LinkedHashSet::new));
    }

    /** Keeps the selected tests that a restart has not left out. */
    private record Selected(SuiteSelection selection, SourceFiles files)
            implements PostDiscoveryFilter {
        private static final FilterResult KEPT = FilterResult.included("selected");

        @Override
        public FilterResult apply(TestDescriptor descriptor) {
            TestId id = TestId.of(descriptor.getUniqueId(), files);
            Set<String> skip = selection.skip();
            if (id.skippedBy(skip) || id.hasInvocationIn(skip)) {
                return FilterResult.excluded("reported before the restart");
            }
            boolean selected = descriptor.isTest()
                    ? selection.selects(id.text())
                    : id.methodSelectedBy(selection);
            return selected ? KEPT : FilterResult.excluded("not selected");
        }
    }
}
