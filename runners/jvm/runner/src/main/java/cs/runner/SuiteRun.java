package cs.runner;

import com.google.gson.JsonObject;
import java.util.Optional;
import java.util.ServiceLoader;
import java.util.function.Consumer;

/**
 * Runs a suite job through the {@link SuiteHost} of its framework and writes its events
 * (docs/specs/runners.md#suite-job): {@code case_start} when a test starts, {@code case_result}
 * when it ends, with what it printed in between and how long it took.
 */
final class SuiteRun implements SuiteListener {
    static final String SUITE_FEATURE = "suite";

    private final EventWriter events;
    private final String jobId;
    private OutputCapture capture;
    private long startedNs;
    private boolean reported;

    private SuiteRun(EventWriter events, String jobId) {
        this.events = events;
        this.jobId = jobId;
    }

    /** Whether a host is on the classpath, so the runner can run suite jobs at all. */
    static boolean available() {
        return ServiceLoader.load(SuiteHost.class).findFirst().isPresent();
    }

    /**
     * The job's events from {@code job_start} to {@code job_end}. A framework missing from the
     * classpath, or one that fails before any test ran, is the job's {@code load_error}.
     */
    static void run(Request.SuiteJob job, EventWriter events) {
        events.jobStart(job.id());
        Optional<SuiteHost> host = host(job.framework());
        if (host.isEmpty()) {
            String message = "the runner's classpath has no " + job.framework() + " host";
            events.loadError(job.id(), new UserError("SuiteUnavailable", message, ""));
        } else {
            new SuiteRun(events, job.id()).runOn(host.get(), job);
        }
        events.jobEnd(job.id());
    }

    private static Optional<SuiteHost> host(String framework) {
        return ServiceLoader.load(SuiteHost.class).stream()
                .map(ServiceLoader.Provider::get)
                .filter(host -> host.framework().equals(framework))
                .findFirst();
    }

    private void runOn(SuiteHost host, Request.SuiteJob job) {
        try {
            host.run(job.root(), job.selection(), this);
        } catch (RuntimeException error) {
            if (reported || capture != null) {
                throw error;
            }
            events.loadError(jobId, UserError.ofFramework(error));
        }
    }

    @Override
    public void started(String testId) {
        events.caseStart(jobId, testId);
        capture = OutputCapture.start();
        startedNs = System.nanoTime();
    }

    @Override
    public void passed(String testId) {
        end(testId, "ok", event -> {
        });
    }

    @Override
    public void failed(String testId, String message, String expected, String actual) {
        end(testId, "failed", event -> {
            event.addProperty("message", message);
            if (expected != null && actual != null) {
                event.addProperty("expected", expected);
                event.addProperty("actual", actual);
            }
        });
    }

    @Override
    public void errored(String testId, Throwable error) {
        end(testId, "error", event -> event.add("error", UserError.ofFramework(error).toJson()));
    }

    @Override
    public void skipped(String testId, String reason) {
        end(testId, "skipped", event -> event.addProperty("message", reason));
    }

    private void end(String testId, String status, Consumer<JsonObject> fields) {
        long durationNs = System.nanoTime() - startedNs;
        String stdout = capture == null ? "" : capture.stop();
        capture = null;
        JsonObject result = new JsonObject();
        result.addProperty("status", status);
        fields.accept(result);
        events.testResult(jobId, testId, result, durationNs, stdout);
        reported = true;
    }
}
