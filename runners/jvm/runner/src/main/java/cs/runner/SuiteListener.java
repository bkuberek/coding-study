package cs.runner;

/**
 * What a {@link SuiteHost} reports about each test: {@link #started} first, then exactly one
 * outcome for the same id. The runner turns them into {@code case_start} and {@code case_result}
 * events, capturing what the test prints in between.
 */
public interface SuiteListener {
    void started(String testId);

    void passed(String testId);

    /**
     * An assertion failed; {@code expected} and {@code actual} are null unless the framework
     * reports both.
     */
    void failed(String testId, String message, String expected, String actual);

    /** Any other exception, in the test or in its setup or teardown. */
    void errored(String testId, Throwable error);

    void skipped(String testId, String reason);
}
