package cs.runner;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import java.util.ArrayList;
import java.util.List;

/** A {@code bench} mode request (docs/specs/runners.md#bench-mode). */
record BenchRequest(List<Job> jobs) implements RunnerRequest {
    private static final String FUNCTION_KIND = "function";
    private static final long NANOSECONDS_PER_MILLISECOND = 1_000_000L;

    /** @param job the target as a test job without cases, so it loads like one */
    record Target(String id, Request.Job job, boolean emitsOutput) {
    }

    /** @param maxBatch at most this many calls, each on a fresh input, per timed sample */
    record Input(int size, Request.Case testCase, int maxBatch) {
    }

    record Settings(
            int reps,
            int warmupMin,
            int warmupMax,
            double warmupCv,
            long budgetNs,
            boolean memory,
            long minSampleNs) {
    }

    record Job(String id, List<Target> targets, List<Input> inputs, Settings settings) {
    }

    static BenchRequest of(JsonObject document) {
        List<Job> jobs = new ArrayList<>();
        for (JsonElement job : Json.array(document, "jobs")) {
            jobs.add(job(Json.asObject(job, "jobs")));
        }
        return new BenchRequest(List.copyOf(jobs));
    }

    private static Job job(JsonObject job) {
        String id = Json.string(job, "job_id");
        List<Target> targets = new ArrayList<>();
        for (JsonElement element : Json.array(job, "targets")) {
            targets.add(target(job, Json.asObject(element, "targets")));
        }
        boolean functionKind = FUNCTION_KIND.equals(Json.string(job, "kind"));
        List<Input> inputs = new ArrayList<>();
        for (JsonElement element : Json.array(job, "inputs")) {
            inputs.add(input(Json.asObject(element, "inputs"), functionKind));
        }
        Settings settings = settings(Json.object(job, "settings"));
        return new Job(id, List.copyOf(targets), List.copyOf(inputs), settings);
    }

    private static Target target(JsonObject job, JsonObject target) {
        String targetId = Json.string(target, "target_id");
        JsonObject asJob = new JsonObject();
        asJob.addProperty("job_id", Json.string(job, "job_id") + "/" + targetId);
        asJob.addProperty("kind", Json.string(job, "kind"));
        asJob.add("target", Json.object(target, "target"));
        asJob.add("names", Json.object(target, "names"));
        asJob.add("signature", Json.object(job, "signature"));
        asJob.add("cases", new JsonArray());
        boolean emitsOutput = target.has("output") && bool(target, "output");
        return new Target(targetId, Request.job(asJob), emitsOutput);
    }

    private static Input input(JsonObject input, boolean functionKind) {
        int size = Json.integer(input, "size");
        String id = "n=" + size;
        Request.Case testCase = functionKind
                ? Request.functionCase(input, id)
                : Request.operationsCase(input, id);
        return new Input(size, testCase, Json.integer(input, "max_batch"));
    }

    private static Settings settings(JsonObject settings) {
        JsonObject warmup = Json.object(settings, "warmup");
        return new Settings(
                Json.integer(settings, "reps"),
                Json.integer(warmup, "min"),
                Json.integer(warmup, "max"),
                number(warmup, "cv"),
                Json.integer(settings, "budget_ms") * NANOSECONDS_PER_MILLISECOND,
                bool(settings, "memory"),
                longInteger(settings, "min_sample_ns"));
    }

    private static double number(JsonObject object, String key) {
        JsonElement value = Json.field(object, key);
        if (!Json.isNumber(value)) {
            throw new BadRequestException("\"" + key + "\" must be a number");
        }
        return value.getAsDouble();
    }

    private static long longInteger(JsonObject object, String key) {
        JsonElement value = Json.field(object, key);
        if (!Json.isNumber(value)) {
            throw new BadRequestException("\"" + key + "\" must be an integer");
        }
        return value.getAsLong();
    }

    private static boolean bool(JsonObject object, String key) {
        JsonElement value = Json.field(object, key);
        if (!Json.isBoolean(value)) {
            throw new BadRequestException("\"" + key + "\" must be true or false");
        }
        return value.getAsBoolean();
    }
}
