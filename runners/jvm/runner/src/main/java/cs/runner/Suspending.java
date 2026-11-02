package cs.runner;

import java.util.Optional;
import java.util.ServiceLoader;

/** The classpath's {@link ClockHost}, the virtual clock of Kotlin projects. */
final class Suspending {
    static final String CLOCK_FEATURE = "clock";
    private static final Optional<ClockHost> HOST = ServiceLoader.load(ClockHost.class).findFirst();

    private Suspending() {
    }

    /** The virtual clock; none without {@code cs.coroutines}. */
    static Optional<ClockHost> host() {
        return HOST;
    }

    /** The host, which a job on the virtual clock needs; without it the target does not load. */
    static ClockHost required(String what) throws LoadException {
        if (HOST.isEmpty()) {
            String message = what + " needs the coroutine bridge on the classpath: the project's "
                    + "build.gradle.kts applies the cs.coroutines plugin";
            throw new LoadException("ClockUnavailable", message);
        }
        return HOST.get();
    }
}
