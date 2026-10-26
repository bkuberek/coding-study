package cs.runner;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonNull;
import com.google.gson.JsonObject;
import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicIntegerArray;

/**
 * One stress run of a concurrent job (docs/specs/runners.md#run-procedure), on platform or
 * virtual threads.
 *
 * <p>Every run is independent: fresh argument decoding, a fresh instance, fresh probe sections
 * and fresh PRNGs. Setup runs on the case thread; the workers wait at a start gate and are
 * released together; the coordinator waits until every worker finished, one failed, or the
 * deadline passed. After a failure or a stall the other workers are interrupted; an
 * {@code InterruptedException} they throw then is not reported.
 */
final class StressRun {
    static final String SETUP = "setup";
    static final String WORKER = "worker";
    static final String FINAL = "final";
    private static final String HARNESS_PREFIX = "@";
    private static final long PRNG_MULTIPLIER = 1_000_003L;
    private static final long LEFTOVER_GRACE_MS = 200;
    private static final long NANOS_PER_MILLI = 1_000_000L;

    /** What a run produced, with the workers that may outlive a failed or stalled run. */
    record Result(CaseResult result, List<Thread> workers) {
        /** Worker threads still alive after a short grace period. */
        int leftoverThreads() throws InterruptedException {
            long deadline = System.nanoTime() + LEFTOVER_GRACE_MS * NANOS_PER_MILLI;
            int alive = 0;
            for (Thread worker : workers) {
                long remaining = Math.max(0, deadline - System.nanoTime());
                if (!worker.join(java.time.Duration.ofNanos(Math.max(1, remaining)))) {
                    alive++;
                }
            }
            return alive;
        }
    }

    /** A decoded op: a method call, or a harness op ({@code call} null). */
    private record Op(String name, JsonArray args, ClassTarget.PreparedOp call) {
    }

    /** Why an op failed, and where. */
    private static final class Failure extends Exception {
        private final transient CaseResult result;
        private final String phase;
        private final int opIndex;
        private final Integer worker;

        Failure(CaseResult result, String phase, int opIndex, Integer worker) {
            super(phase, null, false, false);
            this.result = result;
            this.phase = phase;
            this.opIndex = opIndex;
            this.worker = worker;
        }
    }

    private final ClassTarget target;
    private final Request.StressCase testCase;
    private final Sections sections = new Sections();
    private final Object lock = new Object();
    private final AtomicIntegerArray completed;
    private final AtomicIntegerArray inOp;
    private final AtomicIntegerArray finished;
    private final JsonElement[][] outputs;
    private Failure failure;
    private int finishedCount;
    private volatile boolean stopped;
    private Object instance;
    /** When the gate opened; written and read by the coordinator only. */
    private long startedAt;

    StressRun(ClassTarget target, Request.StressCase testCase) {
        this.target = target;
        this.testCase = testCase;
        int workers = testCase.workers().size();
        this.completed = new AtomicIntegerArray(workers);
        this.inOp = new AtomicIntegerArray(workers);
        this.finished = new AtomicIntegerArray(workers);
        this.outputs = new JsonElement[workers][];
    }

    Result run() throws InterruptedException {
        List<Op> setup;
        List<List<Op>> workers = new ArrayList<>();
        List<Op> finalOps;
        try {
            setup = ops(testCase.setup(), SETUP, null, true);
            for (int ordinal = 0; ordinal < testCase.workers().size(); ordinal++) {
                workers.add(ops(testCase.workers().get(ordinal), WORKER, ordinal, false));
            }
            finalOps = testCase.finalScript() == null
                    ? List.of()
                    : ops(testCase.finalScript(), FINAL, null, false);
        } catch (Failure failed) {
            return new Result(failed(failed, null), List.of());
        }
        JsonArray setupOutputs;
        try {
            setupOutputs = sequence(setup, SETUP, true);
        } catch (Failure failed) {
            return new Result(failed(failed, null), List.of());
        }
        List<Thread> threads = startWorkers(workers);
        return finish(setupOutputs, finalOps, threads);
    }

    private Result finish(JsonArray setupOutputs, List<Op> finalOps, List<Thread> threads)
            throws InterruptedException {
        long durationNs = awaitWorkers();
        Failure failed;
        boolean allFinished;
        synchronized (lock) {
            stopped = true;
            failed = failure;
            allFinished = finishedCount == threads.size();
        }
        if (failed != null || !allFinished) {
            JsonArray progress = unfinished();
            threads.forEach(Thread::interrupt);
            CaseResult result = failed != null
                    ? failed(failed, progress, durationNs)
                    : new CaseResult.Stalled(progress, durationNs);
            return new Result(result, threads);
        }
        JsonArray finalOutputs;
        try {
            finalOutputs = sequence(finalOps, FINAL, false);
        } catch (Failure finalFailure) {
            return new Result(failed(finalFailure, null), threads);
        }
        JsonObject output = new JsonObject();
        output.add("setup", setupOutputs);
        JsonArray workerOutputs = new JsonArray();
        for (JsonElement[] worker : outputs) {
            JsonArray values = new JsonArray();
            for (JsonElement value : worker) {
                values.add(value == null ? JsonNull.INSTANCE : value);
            }
            workerOutputs.add(values);
        }
        output.add("workers", workerOutputs);
        output.add("final", finalOutputs);
        return new Result(
                new CaseResult.StressReturned(output, sections.snapshot(), durationNs), threads);
    }

    /** Step 1: every argument decoded before anything runs. */
    private List<Op> ops(Request.Script script, String phase, Integer worker, boolean constructs)
            throws Failure {
        List<Op> ops = new ArrayList<>();
        for (int index = 0; index < script.ops().size(); index++) {
            String name = script.ops().get(index);
            JsonArray args = script.args().get(index);
            boolean isConstructor = constructs && index == 0;
            if (isConstructor || name.startsWith(HARNESS_PREFIX)) {
                ops.add(new Op(name, args, null));
                continue;
            }
            try {
                ops.add(new Op(name, args, target.prepareOp(name, args)));
            } catch (BadRequestException | IllegalArgumentException error) {
                throw new Failure(invalidInput(error), phase, index, worker);
            }
        }
        return ops;
    }

    private JsonArray sequence(List<Op> ops, String phase, boolean constructs) throws Failure {
        JsonArray results = new JsonArray();
        WorkerHarness harness = new WorkerHarness(sections);
        for (int index = 0; index < ops.size(); index++) {
            Op op = ops.get(index);
            try {
                if (constructs && index == 0) {
                    instance = target.construct(op.args());
                    results.add(JsonNull.INSTANCE);
                } else {
                    results.add(execute(op, harness));
                }
            } catch (Reflection.UserCodeException error) {
                throw new Failure(raised(error.getCause()), phase, index, null);
            } catch (InvalidOutputException error) {
                throw new Failure(invalid(error), phase, index, null);
            } catch (HarnessException error) {
                throw new Failure(harnessError(error), phase, index, null);
            } catch (BadRequestException | IllegalArgumentException error) {
                throw new Failure(invalidInput(error), phase, index, null);
            }
        }
        return results;
    }

    private JsonElement execute(Op op, WorkerHarness harness)
            throws Reflection.UserCodeException, InvalidOutputException, HarnessException {
        if (op.call() == null) {
            harness.run(op.name(), op.args());
            return JsonNull.INSTANCE;
        }
        return ClassTarget.call(op.call(), instance);
    }

    private List<Thread> startWorkers(List<List<Op>> workers) throws InterruptedException {
        CountDownLatch ready = new CountDownLatch(workers.size());
        CountDownLatch go = new CountDownLatch(1);
        List<Thread> threads = new ArrayList<>();
        for (int ordinal = 0; ordinal < workers.size(); ordinal++) {
            int worker = ordinal;
            List<Op> ops = workers.get(ordinal);
            outputs[ordinal] = new JsonElement[ops.size()];
            Runnable body = () -> work(worker, ops, ready, go);
            threads.add(thread(body, ordinal));
        }
        threads.forEach(Thread::start);
        ready.await();
        startedAt = System.nanoTime();
        go.countDown();
        return threads;
    }

    private Thread thread(Runnable body, int ordinal) {
        String name = "cs-worker-" + ordinal;
        if (testCase.virtual()) {
            return Thread.ofVirtual().name(name).unstarted(body);
        }
        Thread thread = new Thread(null, body, name, 0);
        thread.setDaemon(true);
        return thread;
    }

    /** Until every worker finished, one failed, or the deadline passed; returns the duration. */
    private long awaitWorkers() throws InterruptedException {
        long deadline = startedAt + testCase.deadlineMs() * NANOS_PER_MILLI;
        int workers = outputs.length;
        synchronized (lock) {
            while (failure == null && finishedCount < workers) {
                long remaining = deadline - System.nanoTime();
                if (remaining <= 0) {
                    break;
                }
                TimeUnit.NANOSECONDS.timedWait(lock, remaining);
            }
        }
        return System.nanoTime() - startedAt;
    }

    private void work(int ordinal, List<Op> ops, CountDownLatch ready, CountDownLatch go) {
        SplittableRandom random = new SplittableRandom(testCase.seed() * PRNG_MULTIPLIER + ordinal);
        WorkerHarness harness = new WorkerHarness(sections);
        Request.Perturbation perturb = testCase.perturb();
        try {
            ready.countDown();
            go.await();
        } catch (InterruptedException interrupted) {
            return;
        }
        for (int index = 0; index < ops.size(); index++) {
            if (stopped) {
                return;
            }
            if (random.nextDouble() < perturb.yieldProbability()) {
                yieldTimes(1 + random.nextInt(perturb.maxYields()));
            }
            inOp.set(ordinal, 1);
            try {
                outputs[ordinal][index] = execute(ops.get(index), harness);
            } catch (Reflection.UserCodeException error) {
                fail(new Failure(raised(error.getCause()), WORKER, index, ordinal));
                return;
            } catch (InvalidOutputException error) {
                fail(new Failure(invalid(error), WORKER, index, ordinal));
                return;
            } catch (HarnessException error) {
                fail(new Failure(harnessError(error), WORKER, index, ordinal));
                return;
            } catch (RuntimeException error) {
                fail(new Failure(raised(error), WORKER, index, ordinal));
                return;
            }
            completed.set(ordinal, index + 1);
            inOp.set(ordinal, 0);
        }
        synchronized (lock) {
            finished.set(ordinal, 1);
            finishedCount++;
            lock.notifyAll();
        }
    }

    private void fail(Failure failed) {
        synchronized (lock) {
            if (failure == null && !stopped) {
                failure = failed;
            }
            lock.notifyAll();
        }
    }

    private JsonArray unfinished() {
        JsonArray progress = new JsonArray();
        for (int worker = 0; worker < outputs.length; worker++) {
            if (finished.get(worker) == 0) {
                JsonObject item = new JsonObject();
                item.addProperty("worker", worker);
                item.addProperty("completed", completed.get(worker));
                item.addProperty("in_op", inOp.get(worker) == 1);
                progress.add(item);
            }
        }
        return progress;
    }

    static void yieldTimes(int count) {
        for (int index = 0; index < count; index++) {
            Thread.yield();
        }
    }

    private CaseResult raised(Throwable error) {
        return CaseResult.Raised.fromFunction(UserError.of(error, target.userPackage()), 0);
    }

    private static CaseResult invalidInput(RuntimeException error) {
        UserError invalid = new UserError("InvalidInput", String.valueOf(error.getMessage()), "");
        return CaseResult.Raised.fromFunction(invalid, 0);
    }

    private static CaseResult invalid(InvalidOutputException error) {
        return new CaseResult.InvalidOutput(error.getMessage(), 0);
    }

    private static CaseResult harnessError(HarnessException error) {
        return CaseResult.Raised.fromFunction(
                new UserError("HarnessError", error.getMessage(), ""), 0);
    }

    private static CaseResult failed(Failure failed, JsonArray progress) {
        return new CaseResult.StressFailed(
                failed.result, failed.phase, failed.opIndex, failed.worker, progress);
    }

    private static CaseResult failed(Failure failed, JsonArray progress, long durationNs) {
        CaseResult timed = switch (failed.result) {
            case CaseResult.Raised raised -> new CaseResult.Raised(
                    raised.error(), durationNs, raised.opIndex(), raised.partialOutput());
            case CaseResult.InvalidOutput invalid ->
                    new CaseResult.InvalidOutput(invalid.reason(), durationNs);
            default -> failed.result;
        };
        return new CaseResult.StressFailed(
                timed, failed.phase, failed.opIndex, failed.worker, progress);
    }

    /** A harness op that cannot run, such as {@code @exit} without a matching {@code @enter}. */
    static final class HarnessException extends Exception {
        HarnessException(String message) {
            super(message);
        }
    }

    /** One run's probe sections, created on first use, guarded by one monitor. */
    static final class Sections {
        private final java.util.Map<String, int[]> counters = new java.util.LinkedHashMap<>();
        private static final int SHARED = 0;
        private static final int EXCLUSIVE = 1;
        private static final int ENTRIES = 2;
        private static final int VIOLATIONS = 3;
        private static final int MAX_OCCUPANCY = 4;

        synchronized void enter(String name, boolean exclusive) {
            int[] section = counters.computeIfAbsent(name, key -> new int[5]);
            if (exclusive) {
                section[VIOLATIONS] += section[SHARED] + section[EXCLUSIVE] > 0 ? 1 : 0;
                section[EXCLUSIVE]++;
            } else {
                section[VIOLATIONS] += section[EXCLUSIVE] > 0 ? 1 : 0;
                section[SHARED]++;
            }
            section[ENTRIES]++;
            section[MAX_OCCUPANCY] =
                    Math.max(section[MAX_OCCUPANCY], section[SHARED] + section[EXCLUSIVE]);
        }

        synchronized void exit(String name, boolean exclusive) {
            int[] section = counters.get(name);
            section[exclusive ? EXCLUSIVE : SHARED]--;
        }

        synchronized JsonObject snapshot() {
            JsonObject snapshot = new JsonObject();
            counters.forEach((name, section) -> {
                JsonObject counts = new JsonObject();
                counts.addProperty("entries", section[ENTRIES]);
                counts.addProperty("violations", section[VIOLATIONS]);
                counts.addProperty("max_occupancy", section[MAX_OCCUPANCY]);
                snapshot.add(name, counts);
            });
            return snapshot;
        }
    }

    /** One worker's harness ops: the sections it is inside, last entered first. */
    static final class WorkerHarness {
        private static final String ENTER = "@enter";
        private static final String EXIT = "@exit";
        private static final String PAUSE = "@pause";
        private static final String EXCLUSIVE_MODE = "exclusive";
        private static final String SHARED_MODE = "shared";

        private final Sections sections;
        private final java.util.Map<String, java.util.ArrayDeque<Boolean>> entered =
                new java.util.HashMap<>();

        WorkerHarness(Sections sections) {
            this.sections = sections;
        }

        void run(String op, JsonArray args) throws HarnessException {
            if (ENTER.equals(op) && args.size() == 2 && isMode(args.get(1))) {
                String name = args.get(0).getAsString();
                boolean exclusive = EXCLUSIVE_MODE.equals(args.get(1).getAsString());
                sections.enter(name, exclusive);
                entered.computeIfAbsent(name, key -> new java.util.ArrayDeque<>()).push(exclusive);
            } else if (EXIT.equals(op) && args.size() == 1 && Json.isString(args.get(0))) {
                String name = args.get(0).getAsString();
                java.util.ArrayDeque<Boolean> modes = entered.get(name);
                if (modes == null || modes.isEmpty()) {
                    throw new HarnessException("@exit \"" + name + "\" without a matching @enter");
                }
                sections.exit(name, modes.pop());
            } else if (PAUSE.equals(op) && args.size() == 1 && Json.isNumber(args.get(0))) {
                yieldTimes(args.get(0).getAsInt());
            } else {
                throw new HarnessException(op + " cannot take " + args);
            }
        }

        private static boolean isMode(JsonElement mode) {
            return Json.isString(mode)
                    && (EXCLUSIVE_MODE.equals(mode.getAsString())
                            || SHARED_MODE.equals(mode.getAsString()));
        }
    }
}
