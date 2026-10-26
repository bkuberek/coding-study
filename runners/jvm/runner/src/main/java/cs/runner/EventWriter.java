package cs.runner;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import java.io.Closeable;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

/** The {@code --out} event stream: one JSON object per line, flushed immediately. */
final class EventWriter implements Closeable {
    static final String RUNNER = "jvm";
    /** The protocol addition this runner implements (docs/specs/runners.md#capability). */
    static final String STRESS_FEATURE = "stress";
    private static final Gson GSON =
            new GsonBuilder().disableHtmlEscaping().serializeNulls().create();

    private final Writer writer;

    private EventWriter(Writer writer) {
        this.writer = writer;
    }

    static EventWriter open(Path path) throws IOException {
        return new EventWriter(Files.newBufferedWriter(path, StandardCharsets.UTF_8));
    }

    void hello(String runtime) {
        JsonObject event = event("hello");
        event.addProperty("runner", RUNNER);
        event.addProperty("protocol", Request.PROTOCOL);
        event.addProperty("runtime", runtime);
        JsonArray features = new JsonArray();
        features.add(STRESS_FEATURE);
        event.add("features", features);
        write(event);
    }

    /** After a stress run's result, when its worker threads are still alive. */
    void restartRequested(String reason) {
        JsonObject event = event("restart_requested");
        event.addProperty("reason", reason);
        write(event);
    }

    void jobStart(String jobId) {
        write(jobEvent("job_start", jobId));
    }

    void caseStart(String jobId, String caseId) {
        write(caseEvent("case_start", jobId, caseId));
    }

    void caseResult(String jobId, String caseId, CaseResult result, String stdout) {
        JsonObject event = caseEvent("case_result", jobId, caseId);
        result.describe(event);
        event.addProperty("duration_ns", result.durationNs());
        if (!stdout.isEmpty()) {
            event.addProperty("stdout", stdout);
        }
        write(event);
    }

    void loadError(String jobId, UserError error) {
        JsonObject event = jobEvent("load_error", jobId);
        event.add("error", error.toJson());
        write(event);
    }

    void jobEnd(String jobId) {
        write(jobEvent("job_end", jobId));
    }

    /** One target of a bench job at one input size; every bench event names one. */
    record BenchPoint(String jobId, String targetId, int size) {
    }

    /** Bench mode: one target did not load; the job's other targets still run. */
    void targetLoadError(String jobId, String targetId, UserError error) {
        JsonObject event = jobEvent("load_error", jobId);
        event.addProperty("target_id", targetId);
        event.add("error", error.toJson());
        write(event);
    }

    void benchStart(BenchPoint point) {
        write(benchEvent("bench_start", point));
    }

    void benchOutput(BenchPoint point, JsonElement output) {
        JsonObject event = benchEvent("bench_output", point);
        event.add("output", output);
        write(event);
    }

    /** {@code result} is an error or an invalid output; it keeps the fields of a case_result. */
    void benchError(BenchPoint point, CaseResult result) {
        JsonObject event = benchEvent("bench_error", point);
        result.describe(event);
        event.addProperty("duration_ns", result.durationNs());
        write(event);
    }

    void benchSample(BenchPoint point, int rep, long wallNs, long cpuNs, int calls) {
        JsonObject event = benchEvent("bench_sample", point);
        event.addProperty("rep", rep);
        event.addProperty("wall_ns", wallNs);
        event.addProperty("cpu_ns", cpuNs);
        event.addProperty("calls", calls);
        write(event);
    }

    void benchMemory(BenchPoint point, String metric, long bytes) {
        JsonObject event = benchEvent("bench_memory", point);
        event.addProperty("metric", metric);
        event.addProperty("bytes", bytes);
        write(event);
    }

    void benchBudgetExceeded(BenchPoint point, long wallNs) {
        JsonObject event = benchEvent("bench_budget_exceeded", point);
        event.addProperty("wall_ns", wallNs);
        write(event);
    }

    private static JsonObject benchEvent(String name, BenchPoint point) {
        JsonObject event = jobEvent(name, point.jobId());
        event.addProperty("target_id", point.targetId());
        event.addProperty("size", point.size());
        return event;
    }

    void bye() {
        write(event("bye"));
    }

    @Override
    public void close() throws IOException {
        writer.close();
    }

    private static JsonObject event(String name) {
        JsonObject event = new JsonObject();
        event.addProperty("event", name);
        return event;
    }

    private static JsonObject jobEvent(String name, String jobId) {
        JsonObject event = event(name);
        event.addProperty("job_id", jobId);
        return event;
    }

    private static JsonObject caseEvent(String name, String jobId, String caseId) {
        JsonObject event = jobEvent(name, jobId);
        event.addProperty("case_id", caseId);
        return event;
    }

    private void write(JsonObject event) {
        try {
            writer.write(GSON.toJson(event));
            writer.write('\n');
            writer.flush();
        } catch (IOException error) {
            throw new UncheckedIOException(error);
        }
    }
}
