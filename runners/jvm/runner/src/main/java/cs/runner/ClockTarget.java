package cs.runner;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonNull;
import com.google.gson.JsonPrimitive;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * A project's cases on the virtual clock (docs/specs/runners.md#virtual-clock-and-stress-in-
 * project-jobs). The runner decodes each case's operations, the harness operations {@code
 * @advance}, {@code @spawn}, {@code @join} and {@code @now} included, and records their outputs;
 * the classpath's {@link ClockHost} runs them on a test scheduler of the case's own.
 *
 * <p>A deadlock, or a case that ends with coroutines still active, is {@code stalled}, naming
 * the operation and the virtual time. The host cancels what a case leaves, and no coroutine holds
 * a thread, so the next case runs in the same process.
 */
final class ClockTarget implements Target<Request.OperationsCase> {
    static final String ADVANCE = "@advance";
    static final String SPAWN = "@spawn";
    static final String JOIN = "@join";
    static final String NOW = "@now";
    private static final String HARNESS_PREFIX = "@";
    private static final int CONSTRUCTOR_OP = 0;

    private final ClassTarget target;
    private final ClockHost host;

    private ClockTarget(ClassTarget target, ClockHost host) {
        this.target = target;
        this.host = host;
    }

    /** The loaded class's cases on the clock; without a host, the target does not load. */
    static ClockTarget on(ClassTarget target) throws LoadException {
        return new ClockTarget(target, Suspending.required("a project on the virtual clock"));
    }

    @Override
    public PreparedCase prepare(Request.OperationsCase testCase) {
        Steps steps = new Steps(testCase.ops().size());
        for (int op = 0; op < testCase.ops().size(); op++) {
            decode(steps, op, testCase.ops().get(op), testCase.args().get(op));
        }
        return steps::run;
    }

    @Override
    public RawCall prepareCall(Request.OperationsCase testCase) {
        throw new UnsupportedOperationException("a project on the virtual clock has no bench");
    }

    @Override
    public String userPackage() {
        return target.userPackage();
    }

    private void decode(Steps steps, int op, String name, JsonArray args) {
        if (op == CONSTRUCTOR_OP) {
            Object[] arguments = Arguments.decode(target.constructorMember(), args.asList());
            steps.add(name, new ClockStep.Construct(target.constructor(), arguments), null, null);
            return;
        }
        if (!name.startsWith(HARNESS_PREFIX)) {
            ClassTarget.BoundMethod bound = target.method(name);
            Object[] arguments = Arguments.decode(bound.member(), args.asList());
            steps.add(name, call(bound, arguments), bound.member(), arguments);
            return;
        }
        switch (name) {
            case ADVANCE -> steps.add(name, new ClockStep.Advance(milliseconds(args)), null, null);
            case SPAWN -> spawn(steps, args);
            case JOIN -> {
                if (args.size() != 1) {
                    throw new BadRequestException(JOIN + " takes the name of a spawned task");
                }
                steps.join(task(args, JOIN));
            }
            case NOW -> {
                if (!args.isEmpty()) {
                    throw new BadRequestException(NOW + " takes no arguments");
                }
                steps.add(name, new ClockStep.Now(), null, null);
            }
            default -> throw new BadRequestException(
                    "unknown harness operation \"" + name + "\" at index " + op);
        }
    }

    private void spawn(Steps steps, JsonArray args) {
        if (args.size() < 2 || !Json.isString(args.get(1))) {
            throw new BadRequestException(SPAWN + " takes a task name, a method and its arguments");
        }
        String task = task(args, SPAWN);
        ClassTarget.BoundMethod bound = target.method(args.get(1).getAsString());
        List<JsonElement> rest = args.asList().subList(2, args.size());
        Object[] arguments = Arguments.decode(bound.member(), rest);
        steps.spawn(task, call(bound, arguments), bound.member(), arguments);
    }

    private static ClockStep.Call call(ClassTarget.BoundMethod bound, Object[] arguments) {
        return new ClockStep.Call(bound.method(), arguments, bound.member().async());
    }

    private static String task(JsonArray args, String op) {
        if (args.isEmpty() || !Json.isString(args.get(0))) {
            throw new BadRequestException(op + " takes the name of a task first");
        }
        return args.get(0).getAsString();
    }

    private static long milliseconds(JsonArray args) {
        if (args.size() == 1 && Json.isNumber(args.get(0))) {
            JsonPrimitive value = args.get(0).getAsJsonPrimitive();
            long milliseconds = value.getAsLong();
            if (milliseconds >= 0 && milliseconds == value.getAsDouble()) {
                return milliseconds;
            }
        }
        throw new BadRequestException(ADVANCE + " takes a whole number of milliseconds, 0 or more");
    }

    /** One case's decoded operations and the outputs they produced, as the host runs them. */
    private final class Steps implements ClockSteps {
        private final List<String> labels;
        private final List<ClockStep> steps;
        private final List<Member> members;
        private final List<Object[]> arguments;
        /** For a {@code @join}, the index of its {@code @spawn}, whose call it serializes. */
        private final Map<Integer, Integer> spawnOf = new HashMap<>();
        private final Map<String, Integer> openTasks = new HashMap<>();
        private final Outputs.Snapshot[] snapshots;
        private final JsonArray outputs = new JsonArray();
        private String invalid = "";

        Steps(int size) {
            labels = new ArrayList<>(size);
            steps = new ArrayList<>(size);
            members = new ArrayList<>(size);
            arguments = new ArrayList<>(size);
            snapshots = new Outputs.Snapshot[size];
        }

        void add(String label, ClockStep step, Member member, Object[] callArguments) {
            labels.add(label);
            steps.add(step);
            members.add(member);
            arguments.add(callArguments);
        }

        void spawn(String task, ClockStep.Call call, Member member, Object[] callArguments) {
            if (openTasks.containsKey(task)) {
                throw new BadRequestException("task \"" + task + "\" was spawned and not joined yet");
            }
            openTasks.put(task, steps.size());
            add(SPAWN + " " + task, new ClockStep.Spawn(task, call), member, callArguments);
        }

        void join(String task) {
            Integer spawn = openTasks.remove(task);
            if (spawn == null) {
                throw new BadRequestException(JOIN + " of task \"" + task + "\", which no "
                        + SPAWN + " started");
            }
            spawnOf.put(steps.size(), spawn);
            add(JOIN + " " + task, new ClockStep.Join(task), null, null);
        }

        @Override
        public int size() {
            return steps.size();
        }

        @Override
        public ClockStep step(int index) {
            ClockStep step = steps.get(index);
            if (step instanceof ClockStep.Call || step instanceof ClockStep.Spawn) {
                snapshots[index] = Outputs.beforeCall(members.get(index), arguments.get(index));
            }
            return step;
        }

        @Override
        public boolean returned(int index, Object value) {
            try {
                outputs.add(output(index, value));
                return true;
            } catch (InvalidOutputException error) {
                invalid = reason(index, error.getMessage());
                return false;
            }
        }

        private JsonElement output(int index, Object value) throws InvalidOutputException {
            return switch (steps.get(index)) {
                case ClockStep.Call call -> serialized(index, value);
                case ClockStep.Join join -> serialized(spawnOf.get(index), value);
                case ClockStep.Now now -> new JsonPrimitive(((Number) value).longValue());
                case ClockStep.Construct construct -> JsonNull.INSTANCE;
                case ClockStep.Advance advance -> JsonNull.INSTANCE;
                case ClockStep.Spawn spawn -> JsonNull.INSTANCE;
            };
        }

        private JsonElement serialized(int call, Object value) throws InvalidOutputException {
            return Outputs.serialize(members.get(call), arguments.get(call), value, snapshots[call]);
        }

        CaseResult run() {
            long start = System.nanoTime();
            ClockEnd end = host.run(this);
            long durationNs = System.nanoTime() - start;
            return switch (end) {
                case ClockEnd.Finished finished -> new CaseResult.Returned(outputs, durationNs);
                case ClockEnd.Failed failed -> new CaseResult.Raised(
                        UserError.of(failed.error(), userPackage()),
                        durationNs,
                        failed.index(),
                        partial(failed.index()));
                case ClockEnd.Refused refused -> new CaseResult.InvalidOutput(invalid, durationNs);
                case ClockEnd.Deadlocked deadlocked -> new CaseResult.ClockStalled(
                        reason(deadlocked.index(),
                                "deadlock at " + deadlocked.milliseconds() + " ms"),
                        deadlocked.index(),
                        partial(deadlocked.index()),
                        durationNs);
                case ClockEnd.LeftActive left -> new CaseResult.ClockStalled(
                        reason(left.index(), "the case ended with coroutines still active at "
                                + left.milliseconds() + " ms"),
                        left.index(),
                        partial(left.index()),
                        durationNs);
            };
        }

        private String reason(int index, String what) {
            return "op " + index + " (" + labels.get(index) + "): " + what;
        }

        /** The outputs of the operations before {@code index}. */
        private JsonArray partial(int index) {
            JsonArray partial = new JsonArray();
            for (int op = 0; op < index && op < outputs.size(); op++) {
                partial.add(outputs.get(op));
            }
            return partial;
        }
    }
}
