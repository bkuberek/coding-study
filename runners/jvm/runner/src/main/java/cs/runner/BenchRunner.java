package cs.runner;

import java.lang.management.ManagementFactory;
import java.lang.management.ThreadMXBean;
import java.lang.ref.Reference;
import java.util.ArrayList;
import java.util.List;

/**
 * Bench mode (docs/specs/runners.md#bench-mode).
 *
 * <p>Per size, in request order: each target makes one check call through the test path (its
 * output is reported for output targets), then warmup samples until the timings settle (or have
 * taken the per-call budget in total), then the timed repetitions take turns across targets, then
 * one memory call per target. Every call, or
 * batch of calls, is announced with {@code bench_start} first, so the CLI can attribute a hang.
 *
 * <p>A sample makes {@code calls} back-to-back calls, each on its own freshly decoded input.
 * Decoding and the {@code System.gc()} hint happen outside the timed region; results stay
 * reachable until the sample ends.
 */
final class BenchRunner {
    private static final String MEMORY_METRIC = "thread_allocated_bytes";
    private static final int CV_WINDOW = 5;

    private final EventWriter events;
    private final ThreadMXBean threads = ManagementFactory.getThreadMXBean();

    BenchRunner(EventWriter events) {
        this.events = events;
    }

    void run(BenchRequest request) {
        for (BenchRequest.Job job : request.jobs()) {
            events.jobStart(job.id());
            List<Running> running = new ArrayList<>();
            for (BenchRequest.Target target : job.targets()) {
                try {
                    running.add(new Running(target, AnyTarget.load(target.job())));
                } catch (LoadException error) {
                    events.targetLoadError(job.id(), target.id(), error.error());
                }
            }
            new Session(job).run(running);
            events.jobEnd(job.id());
        }
    }

    /** A loaded target that takes any input of its job's kind. */
    private interface AnyTarget {
        Target.PreparedCase prepare(Request.Case testCase);

        Target.RawCall prepareCall(Request.Case testCase) throws Reflection.UserCodeException;

        String userPackage();

        static AnyTarget load(Request.Job job) throws LoadException {
            return switch (job) {
                case Request.FunctionJob function ->
                        of(FunctionTarget.load(function), Request.FunctionCase.class);
                case Request.ClassJob design ->
                        of(ClassTarget.load(design), Request.OperationsCase.class);
                case Request.ConcurrentJob concurrent ->
                        throw new BadRequestException("concurrent problems have no bench");
            };
        }

        private static <C extends Request.Case> AnyTarget of(Target<C> target, Class<C> type) {
            return new AnyTarget() {
                @Override
                public Target.PreparedCase prepare(Request.Case testCase) {
                    return target.prepare(cast(testCase));
                }

                @Override
                public Target.RawCall prepareCall(Request.Case testCase)
                        throws Reflection.UserCodeException {
                    return target.prepareCall(cast(testCase));
                }

                @Override
                public String userPackage() {
                    return target.userPackage();
                }

                private C cast(Request.Case testCase) {
                    if (!type.isInstance(testCase)) {
                        throw new BadRequestException("bench input does not fit the job kind");
                    }
                    return type.cast(testCase);
                }
            };
        }
    }

    private static final class Running {
        final BenchRequest.Target spec;
        final AnyTarget target;
        int calls = 1;

        Running(BenchRequest.Target spec, AnyTarget target) {
            this.spec = spec;
            this.target = target;
        }
    }

    private record Sample(long wallNs, long cpuNs, int calls) {
        long perCallNs() {
            return wallNs / calls;
        }
    }

    private final class Session {
        private final BenchRequest.Job job;
        private final BenchRequest.Settings settings;

        Session(BenchRequest.Job job) {
            this.job = job;
            this.settings = job.settings();
        }

        void run(List<Running> targets) {
            List<Running> active = new ArrayList<>(targets);
            for (BenchRequest.Input input : job.inputs()) {
                active.removeIf(target -> !warmUp(target, input));
                repetitions(active, input);
                if (settings.memory()) {
                    active.removeIf(target -> !memory(target, input));
                }
            }
        }

        /** The check call, then warmup samples; false once the target is dropped. */
        private boolean warmUp(Running target, BenchRequest.Input input) {
            EventWriter.BenchPoint point = start(target, input);
            CaseResult check = check(target, input);
            if (!(check instanceof CaseResult.Returned returned)) {
                events.benchError(point, check);
                return false;
            }
            if (target.spec.emitsOutput()) {
                events.benchOutput(point, returned.output());
            }
            if (overBudget(point, check.durationNs())) {
                return false;
            }
            target.calls = batch(input, 1, check.durationNs());
            List<Long> runs = new ArrayList<>(List.of(check.durationNs()));
            long warmupStarted = System.nanoTime();
            while (!settled(runs) && !warmedFor(warmupStarted)) {
                Sample sample = sample(target, input);
                if (sample == null || overBudget(point(target, input), sample.perCallNs())) {
                    return false;
                }
                runs.add(sample.perCallNs());
                target.calls = batch(input, target.calls, sample.wallNs());
            }
            return true;
        }

        /** Warmup, decoding and collection included, has taken the per-call budget. */
        private boolean warmedFor(long startedNs) {
            return System.nanoTime() - startedNs >= settings.budgetNs();
        }

        private CaseResult check(Running target, BenchRequest.Input input) {
            Target.PreparedCase prepared = target.target.prepare(input.testCase());
            OutputCapture capture = OutputCapture.start();
            try {
                return prepared.run();
            } finally {
                capture.stop();
            }
        }

        private void repetitions(List<Running> active, BenchRequest.Input input) {
            for (int rep = 1; rep <= settings.reps(); rep++) {
                for (Running target : List.copyOf(active)) {
                    Sample sample = sample(target, input);
                    EventWriter.BenchPoint point = point(target, input);
                    if (sample == null || overBudget(point, sample.perCallNs())) {
                        active.remove(target);
                        continue;
                    }
                    events.benchSample(point, rep, sample.wallNs(), sample.cpuNs(), sample.calls());
                }
            }
        }

        /** Bytes this thread allocated during one call; false when the call fails. */
        private boolean memory(Running target, BenchRequest.Input input) {
            if (!(threads instanceof com.sun.management.ThreadMXBean allocations)) {
                return true;
            }
            EventWriter.BenchPoint point = start(target, input);
            long threadId = Thread.currentThread().threadId();
            Object result;
            long allocated;
            try {
                Target.RawCall call = target.target.prepareCall(input.testCase());
                System.gc();
                long before = allocations.getThreadAllocatedBytes(threadId);
                result = call.call();
                allocated = allocations.getThreadAllocatedBytes(threadId) - before;
            } catch (Reflection.UserCodeException error) {
                failed(target, point, error);
                return false;
            }
            Reference.reachabilityFence(result);
            events.benchMemory(point, MEMORY_METRIC, Math.max(0, allocated));
            return true;
        }

        private Sample sample(Running target, BenchRequest.Input input) {
            EventWriter.BenchPoint point = start(target, input);
            Target.RawCall[] calls = new Target.RawCall[target.calls];
            Object[] results = new Object[target.calls];
            try {
                for (int index = 0; index < calls.length; index++) {
                    calls[index] = target.target.prepareCall(input.testCase());
                }
            } catch (Reflection.UserCodeException error) {
                failed(target, point, error);
                return null;
            }
            System.gc();
            long cpuStarted = threads.getCurrentThreadCpuTime();
            long started = System.nanoTime();
            try {
                for (int index = 0; index < calls.length; index++) {
                    results[index] = calls[index].call();
                }
            } catch (Reflection.UserCodeException error) {
                failed(target, point, error, System.nanoTime() - started);
                return null;
            }
            long wallNs = System.nanoTime() - started;
            long cpuNs = threads.getCurrentThreadCpuTime() - cpuStarted;
            Reference.reachabilityFence(results);
            return new Sample(wallNs, cpuNs, calls.length);
        }

        private boolean settled(List<Long> runs) {
            if (runs.size() >= settings.warmupMax()) {
                return true;
            }
            if (runs.size() < settings.warmupMin()) {
                return false;
            }
            List<Long> latest = runs.subList(Math.max(0, runs.size() - CV_WINDOW), runs.size());
            return latest.size() > 1 && coefficientOfVariation(latest) <= settings.warmupCv();
        }

        private int batch(BenchRequest.Input input, int calls, long sampleNs) {
            long minimum = settings.minSampleNs();
            if (sampleNs >= minimum) {
                return calls;
            }
            long wanted = (long) Math.ceil((double) calls * minimum / Math.max(sampleNs, 1));
            return (int) Math.max(calls, Math.min(wanted, input.maxBatch()));
        }

        private boolean overBudget(EventWriter.BenchPoint point, long perCallNs) {
            if (perCallNs <= settings.budgetNs()) {
                return false;
            }
            events.benchBudgetExceeded(point, perCallNs);
            return true;
        }

        private void failed(
                Running target, EventWriter.BenchPoint point, Reflection.UserCodeException error) {
            failed(target, point, error, 0);
        }

        private void failed(
                Running target,
                EventWriter.BenchPoint point,
                Reflection.UserCodeException error,
                long durationNs) {
            UserError raised = UserError.of(error.getCause(), target.target.userPackage());
            events.benchError(point, CaseResult.Raised.fromFunction(raised, durationNs));
        }

        private EventWriter.BenchPoint start(Running target, BenchRequest.Input input) {
            EventWriter.BenchPoint point = point(target, input);
            events.benchStart(point);
            return point;
        }

        private EventWriter.BenchPoint point(Running target, BenchRequest.Input input) {
            return new EventWriter.BenchPoint(job.id(), target.spec.id(), input.size());
        }
    }

    private static double coefficientOfVariation(List<Long> values) {
        double mean = values.stream().mapToLong(Long::longValue).average().orElse(0);
        if (mean == 0) {
            return 0;
        }
        double variance = values.stream()
                .mapToDouble(value -> (value - mean) * (value - mean))
                .average()
                .orElse(0);
        return Math.sqrt(variance) / mean;
    }
}
