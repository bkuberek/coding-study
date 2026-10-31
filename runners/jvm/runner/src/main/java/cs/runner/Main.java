package cs.runner;

import java.io.PrintStream;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;

/**
 * The JVM runner for Java and Kotlin: {@code java -cp <classpath> cs.runner.Main --request R
 * --out O} (docs/specs/runners.md).
 *
 * <p>Exit codes: 0 once {@code bye} is written, 2 for a bad request while no case is in progress,
 * 3 after {@code restart_requested} (a stress run left worker threads alive), 1 for an internal
 * failure. Cases run on a thread with a 256 MiB stack for deep recursion.
 */
public final class Main {
    static final int EXIT_OK = 0;
    static final int EXIT_INTERNAL_ERROR = 1;
    static final int EXIT_BAD_REQUEST = 2;
    static final int EXIT_RESTART = 3;
    private static final long CASE_STACK_BYTES = 256L * 1024 * 1024;
    private static final String REQUEST_FLAG = "--request";
    private static final String OUT_FLAG = "--out";
    private static final String STRESS_FEATURE = "stress";
    private static final String PROJECT_FEATURE = "project";

    private Main() {
    }

    public static void main(String[] args) {
        PrintStream diagnostics = System.err;
        int exitCode;
        try {
            exitCode = run(args);
        } catch (JobRunner.RestartRequestedException restart) {
            exitCode = EXIT_RESTART;
        } catch (BadRequestException error) {
            diagnostics.println("cs.runner: bad request: " + error.getMessage());
            exitCode = EXIT_BAD_REQUEST;
        } catch (Throwable error) {
            error.printStackTrace(diagnostics);
            exitCode = EXIT_INTERNAL_ERROR;
        }
        System.exit(exitCode);
    }

    private static int run(String[] args) throws Throwable {
        Path requestPath = Path.of(option(args, REQUEST_FLAG));
        Path outPath = Path.of(option(args, OUT_FLAG));
        RunnerRequest request = RunnerRequest.read(requestPath);
        try (EventWriter events = EventWriter.open(outPath)) {
            events.hello(System.getProperty("java.version"), features());
            runOnLargeStack(() -> run(request, events));
            events.bye();
        }
        return EXIT_OK;
    }

    /**
     * Stress runs and project grading always; suite jobs when a test framework host is on the
     * classpath, as on a project's test runtime classpath (docs/specs/runners.md#capability).
     */
    private static List<String> features() {
        List<String> features = new ArrayList<>(List.of(STRESS_FEATURE, PROJECT_FEATURE));
        if (SuiteRun.available()) {
            features.add(SuiteRun.SUITE_FEATURE);
        }
        return features;
    }

    private static void run(RunnerRequest request, EventWriter events) {
        switch (request) {
            case Request test -> new JobRunner(events).run(test);
            case BenchRequest bench -> new BenchRunner(events).run(bench);
        }
    }

    private static void runOnLargeStack(Runnable work) throws Throwable {
        AtomicReference<Throwable> failure = new AtomicReference<>();
        Runnable guarded = () -> {
            try {
                work.run();
            } catch (Throwable error) {
                failure.set(error);
            }
        };
        Thread worker = new Thread(null, guarded, "cs-runner-cases", CASE_STACK_BYTES);
        worker.start();
        worker.join();
        if (failure.get() != null) {
            throw failure.get();
        }
    }

    private static String option(String[] args, String flag) {
        for (int index = 0; index + 1 < args.length; index++) {
            if (args[index].equals(flag)) {
                return args[index + 1];
            }
        }
        throw new BadRequestException("missing " + flag);
    }
}
