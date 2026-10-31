package cs.runner;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParseException;
import com.google.gson.JsonParser;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** A {@code test} mode request (docs/specs/runners.md#request-file). */
record Request(List<Job> jobs) implements RunnerRequest {
    static final int PROTOCOL = 1;
    private static final String FUNCTION_KIND = "function";
    private static final String CONCURRENT_KIND = "concurrent";
    private static final String SUITE_KIND = "suite";
    private static final String THREADS_MODEL = "threads";
    private static final String PLATFORM = "platform";

    /** The input of one call: function arguments or an operation sequence. */
    sealed interface Case permits FunctionCase, OperationsCase, StressCase {
        String id();
    }

    sealed interface Job permits FunctionJob, ClassJob, ConcurrentJob, SuiteJob {
        String id();
    }

    /** @param className the fully qualified class from {@code target.class} */
    record FunctionJob(String id, String className, Member function, List<FunctionCase> cases)
            implements Job {
    }

    /**
     * A project's native tests (docs/specs/runners.md#suite-job): no target and no cases, since
     * the framework discovers the tests. {@code exclude} is not read: the build already left
     * those files out.
     */
    record SuiteJob(String id, String framework, Path root, SuiteSelection selection)
            implements Job {
    }

    /**
     * @param className the fully qualified class from {@code target.class}
     * @param methods keyed by canonical method name, as {@code ops} names them
     */
    record ClassJob(
            String id,
            String className,
            Member constructor,
            Map<String, Member> methods,
            List<OperationsCase> cases) implements Job {
    }

    /**
     * A concurrent job (docs/specs/runners.md#concurrent-jobs): sequential {@link OperationsCase}s,
     * then {@link StressCase}s; the JVM runs the threads model only.
     */
    record ConcurrentJob(
            String id,
            String className,
            Member constructor,
            Map<String, Member> methods,
            List<Case> cases) implements Job {
        /** The class as a design job without cases, so it loads like one. */
        ClassJob design() {
            return new ClassJob(id, className, constructor, methods, List.of());
        }
    }

    /** Ops and their arguments; worker and final scripts have no constructor. */
    record Script(List<String> ops, List<JsonArray> args) {
    }

    record Perturbation(double yieldProbability, int maxYields) {
    }

    /**
     * One stress run: setup, worker scripts released together, then an optional final script.
     *
     * @param seed already the case's seed plus the run index
     * @param virtual true for virtual worker threads, false for platform threads
     * @param finalScript null when the case has no final sequence
     */
    record StressCase(
            String id,
            long seed,
            boolean virtual,
            long deadlineMs,
            Perturbation perturb,
            Script setup,
            List<Script> workers,
            Script finalScript) implements Case {
    }

    /** @param input keyed by canonical parameter name */
    record FunctionCase(String id, JsonObject input) implements Case {
    }

    record OperationsCase(String id, List<String> ops, List<JsonArray> args) implements Case {
    }

    static Request of(JsonObject document) {
        List<Job> jobs = new ArrayList<>();
        for (JsonElement job : Json.array(document, "jobs")) {
            jobs.add(job(Json.asObject(job, "jobs")));
        }
        return new Request(List.copyOf(jobs));
    }

    static JsonElement parse(Path path) {
        try {
            return JsonParser.parseString(Files.readString(path, StandardCharsets.UTF_8));
        } catch (IOException | JsonParseException error) {
            String reason = error.getMessage();
            throw new BadRequestException("cannot read request " + path + ": " + reason);
        }
    }

    static Job job(JsonObject job) {
        String id = Json.string(job, "job_id");
        if (SUITE_KIND.equals(Json.string(job, "kind"))) {
            return suiteJob(job, id);
        }
        String className = Json.string(Json.object(job, "target"), "class");
        JsonObject names = Json.object(job, "names");
        JsonObject signature = Json.object(job, "signature");
        JsonArray cases = Json.array(job, "cases");
        if (FUNCTION_KIND.equals(Json.string(job, "kind"))) {
            Member function = Member.parse(
                    Json.string(names, "function"), Json.object(signature, "function"));
            return new FunctionJob(id, className, function, functionCases(cases));
        }
        JsonObject classSignature = Json.object(signature, "class");
        Member constructor = Member.constructor(
                Json.string(names, "class"), Json.object(classSignature, "constructor"));
        Map<String, Member> methods =
                methods(Json.array(classSignature, "methods"), Json.object(names, "methods"));
        if (CONCURRENT_KIND.equals(Json.string(job, "kind"))) {
            String model = Json.string(job, "model");
            if (!THREADS_MODEL.equals(model)) {
                throw new BadRequestException("the JVM runs the threads model only, not " + model);
            }
            return new ConcurrentJob(id, className, constructor, methods, concurrentCases(cases));
        }
        return new ClassJob(id, className, constructor, methods, operationsCases(cases));
    }

    private static SuiteJob suiteJob(JsonObject job, String id) {
        SuiteSelection selection =
                new SuiteSelection(strings(job, "select"), new HashSet<>(strings(job, "skip")));
        Path root = Path.of(Json.string(job, "root"));
        return new SuiteJob(id, Json.string(job, "framework"), root, selection);
    }

    private static List<String> strings(JsonObject object, String key) {
        List<String> values = new ArrayList<>();
        for (JsonElement value : Json.array(object, key)) {
            if (!Json.isString(value)) {
                throw new BadRequestException("\"" + key + "\" must hold strings");
            }
            values.add(value.getAsString());
        }
        return List.copyOf(values);
    }

    private static List<Case> concurrentCases(JsonArray cases) {
        List<Case> parsed = new ArrayList<>();
        for (JsonElement element : cases) {
            JsonObject testCase = Json.asObject(element, "cases");
            String id = Json.string(testCase, "id");
            parsed.add(testCase.has("stress")
                    ? stressCase(Json.object(testCase, "stress"), id)
                    : operationsCase(testCase, id));
        }
        return List.copyOf(parsed);
    }

    private static StressCase stressCase(JsonObject stress, String id) {
        JsonObject perturb = Json.object(stress, "perturb");
        String threadKind = stress.has("thread_kind") ? Json.string(stress, "thread_kind") : PLATFORM;
        List<Script> workers = new ArrayList<>();
        for (JsonElement worker : Json.array(stress, "workers")) {
            workers.add(script(Json.asObject(worker, "workers")));
        }
        return new StressCase(
                id,
                Json.field(stress, "seed").getAsLong(),
                !PLATFORM.equals(threadKind),
                Json.integer(stress, "deadline_ms"),
                new Perturbation(
                        Json.field(perturb, "yield_probability").getAsDouble(),
                        Json.integer(perturb, "max_yields")),
                script(Json.object(stress, "setup")),
                List.copyOf(workers),
                stress.has("final") ? script(Json.object(stress, "final")) : null);
    }

    private static Script script(JsonObject script) {
        List<String> ops = new ArrayList<>();
        for (JsonElement op : Json.array(script, "ops")) {
            if (!Json.isString(op)) {
                throw new BadRequestException("\"ops\" must hold strings");
            }
            ops.add(op.getAsString());
        }
        List<JsonArray> args = new ArrayList<>();
        for (JsonElement arguments : Json.array(script, "args")) {
            args.add(Json.asArray(arguments, "args"));
        }
        if (ops.size() != args.size()) {
            throw new BadRequestException("a script needs one argument array per op");
        }
        return new Script(List.copyOf(ops), List.copyOf(args));
    }

    private static Map<String, Member> methods(JsonArray signatures, JsonObject names) {
        Map<String, Member> methods = new LinkedHashMap<>();
        for (JsonElement element : signatures) {
            JsonObject method = Json.asObject(element, "methods");
            String canonical = Json.string(method, "name");
            methods.put(canonical, Member.parse(Json.string(names, canonical), method));
        }
        return methods;
    }

    private static List<FunctionCase> functionCases(JsonArray cases) {
        List<FunctionCase> parsed = new ArrayList<>();
        for (JsonElement element : cases) {
            JsonObject testCase = Json.asObject(element, "cases");
            parsed.add(functionCase(testCase, Json.string(testCase, "id")));
        }
        return List.copyOf(parsed);
    }

    private static List<OperationsCase> operationsCases(JsonArray cases) {
        List<OperationsCase> parsed = new ArrayList<>();
        for (JsonElement element : cases) {
            JsonObject testCase = Json.asObject(element, "cases");
            parsed.add(operationsCase(testCase, Json.string(testCase, "id")));
        }
        return List.copyOf(parsed);
    }

    static FunctionCase functionCase(JsonObject testCase, String id) {
        return new FunctionCase(id, Json.object(testCase, "input"));
    }

    static OperationsCase operationsCase(JsonObject testCase, String id) {
        List<String> ops = new ArrayList<>();
        for (JsonElement op : Json.array(testCase, "ops")) {
            if (!Json.isString(op)) {
                throw new BadRequestException("\"ops\" must hold strings");
            }
            ops.add(op.getAsString());
        }
        List<JsonArray> args = new ArrayList<>();
        for (JsonElement arguments : Json.array(testCase, "args")) {
            args.add(Json.asArray(arguments, "args"));
        }
        if (ops.isEmpty() || ops.size() != args.size()) {
            throw new BadRequestException("ops and args must be non-empty and equally long");
        }
        return new OperationsCase(id, ops, args);
    }
}
