package cs.runner;

import java.nio.file.Path;

/**
 * A test framework the runner hosts for suite jobs (docs/specs/runners.md#suite-job).
 *
 * <p>The runner finds hosts with {@link java.util.ServiceLoader}: a project's test runtime
 * classpath holds one, the classpath of a single-file problem none, and {@code hello} lists the
 * {@code suite} feature only when one is there.
 */
public interface SuiteHost {
    /** The request's {@code framework}, such as {@code junit-platform}. */
    String framework();

    /**
     * Discovers the tests of the project at {@code root} and runs those {@code selection} keeps,
     * reporting each one to {@code tests} as it starts and as it ends, in the order they run.
     */
    void run(Path root, SuiteSelection selection, SuiteListener tests);
}
