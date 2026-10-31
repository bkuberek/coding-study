package cs.suite;

import cs.runner.SuiteListener;
import org.junit.platform.engine.TestExecutionResult;
import org.junit.platform.launcher.TestExecutionListener;
import org.junit.platform.launcher.TestIdentifier;
import org.opentest4j.AssertionFailedError;

/**
 * Turns JUnit Platform's execution events into the runner's (docs/specs/runners.md#suite-job).
 *
 * <p>Every test is reported. A container is reported, under its own id, only when it does not
 * pass as a whole: a class whose {@code @BeforeAll} or {@code @AfterAll} failed is an error, a
 * disabled class or one whose assumption failed in its setup is skipped, since none of its tests
 * report it. An {@link AssertionError} fails a test, with expected and actual when opentest4j
 * carries both (JUnit's {@code assertEquals} and kotlin.test's); any other exception is an error.
 */
final class Reporter implements TestExecutionListener {
    private static final String ABORTED = "aborted: ";

    private final SuiteListener tests;
    private final SourceFiles files;

    Reporter(SuiteListener tests, SourceFiles files) {
        this.tests = tests;
        this.files = files;
    }

    @Override
    public void executionStarted(TestIdentifier test) {
        if (test.isTest()) {
            tests.started(id(test));
        }
    }

    @Override
    public void executionSkipped(TestIdentifier test, String reason) {
        TestId id = TestId.of(test.getUniqueIdObject(), files);
        if (test.isTest() || !id.classes().isEmpty()) {
            tests.started(id.text());
            tests.skipped(id.text(), reason);
        }
    }

    @Override
    public void executionFinished(TestIdentifier test, TestExecutionResult result) {
        boolean passed = result.getStatus() == TestExecutionResult.Status.SUCCESSFUL;
        if (test.isTest()) {
            report(id(test), result);
        } else if (!passed) {
            String id = id(test);
            tests.started(id);
            report(id, result);
        }
    }

    private void report(String id, TestExecutionResult result) {
        Throwable error = result.getThrowable().orElse(null);
        switch (result.getStatus()) {
            case SUCCESSFUL -> tests.passed(id);
            case ABORTED -> tests.skipped(id, ABORTED + message(error));
            case FAILED -> {
                if (error instanceof AssertionError assertion) {
                    failed(id, assertion);
                } else {
                    tests.errored(id, error);
                }
            }
        }
    }

    private void failed(String id, AssertionError assertion) {
        if (assertion instanceof AssertionFailedError compared
                && compared.isExpectedDefined()
                && compared.isActualDefined()) {
            String expected = compared.getExpected().getStringRepresentation();
            String actual = compared.getActual().getStringRepresentation();
            tests.failed(id, message(assertion), expected, actual);
        } else {
            tests.failed(id, message(assertion), null, null);
        }
    }

    private String id(TestIdentifier test) {
        return TestId.of(test.getUniqueIdObject(), files).text();
    }

    private static String message(Throwable error) {
        if (error == null) {
            return "";
        }
        String message = error.getMessage();
        return message == null ? error.getClass().getSimpleName() : message;
    }
}
