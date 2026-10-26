package cs.runner;

import java.util.List;
import java.util.function.Function;

/** Runs every job of a request in order and reports each one on the event stream. */
final class JobRunner {
    /** A stress run left worker threads alive; the runner exits with code 3 after reporting it. */
    static final class RestartRequestedException extends RuntimeException {
        RestartRequestedException(String reason) {
            super(reason, null, false, false);
        }
    }

    private final EventWriter events;

    JobRunner(EventWriter events) {
        this.events = events;
    }

    void run(Request request) {
        for (Request.Job job : request.jobs()) {
            events.jobStart(job.id());
            try {
                runCases(job);
            } catch (LoadException error) {
                events.loadError(job.id(), error.error());
            }
            events.jobEnd(job.id());
        }
    }

    private void runCases(Request.Job job) throws LoadException {
        switch (job) {
            case Request.FunctionJob function -> runCases(
                    function.id(),
                    function.cases(),
                    FunctionTarget.load(function),
                    Request.FunctionCase::id);
            case Request.ClassJob design -> runCases(
                    design.id(),
                    design.cases(),
                    ClassTarget.load(design),
                    Request.OperationsCase::id);
            case Request.ConcurrentJob concurrent -> runConcurrent(concurrent);
        }
    }

    /** Sequential cases like a design problem's, then stress runs (runners.md#concurrent-jobs). */
    private void runConcurrent(Request.ConcurrentJob job) throws LoadException {
        ClassTarget target = ClassTarget.load(job.design());
        for (Request.Case testCase : job.cases()) {
            switch (testCase) {
                case Request.OperationsCase sequence ->
                        runCases(job.id(), List.of(sequence), target, Request.OperationsCase::id);
                case Request.StressCase stress -> runStress(job.id(), target, stress);
                case Request.FunctionCase function ->
                        throw new BadRequestException("a concurrent job has no function cases");
            }
        }
    }

    private void runStress(String jobId, ClassTarget target, Request.StressCase stress) {
        events.caseStart(jobId, stress.id());
        OutputCapture capture = OutputCapture.start();
        StressRun.Result result;
        String stdout;
        try {
            result = new StressRun(target, stress).run();
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("the case thread was interrupted", interrupted);
        } finally {
            stdout = capture.stop();
        }
        events.caseResult(jobId, stress.id(), result.result(), stdout);
        int leftovers;
        try {
            leftovers = result.leftoverThreads();
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
            leftovers = result.workers().size();
        }
        if (leftovers > 0) {
            String reason = leftovers + " worker threads still alive after " + stress.id();
            events.restartRequested(reason);
            throw new RestartRequestedException(reason);
        }
    }

    private <C> void runCases(
            String jobId, List<C> cases, Target<C> target, Function<C, String> caseId) {
        for (C testCase : cases) {
            Target.PreparedCase prepared = target.prepare(testCase);
            String id = caseId.apply(testCase);
            events.caseStart(jobId, id);
            OutputCapture capture = OutputCapture.start();
            CaseResult result;
            String stdout;
            try {
                result = prepared.run();
            } finally {
                stdout = capture.stop();
            }
            events.caseResult(jobId, id, result, stdout);
        }
    }
}
