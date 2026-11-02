package cs.runner;

import java.lang.reflect.Method;
import java.util.Optional;
import java.util.ServiceLoader;

/**
 * The classpath's {@link ClockHost}, and calls of Kotlin {@code suspend} methods outside the
 * virtual clock: a stress worker blocks its thread until the call returns, on the real clock.
 */
final class Suspending {
    static final String CLOCK_FEATURE = "clock";
    private static final Optional<ClockHost> HOST = ServiceLoader.load(ClockHost.class).findFirst();

    private Suspending() {
    }

    /** The virtual clock and the caller of suspend methods; none without {@code cs.coroutines}. */
    static Optional<ClockHost> host() {
        return HOST;
    }

    /**
     * The host, which a target with a {@code suspend} method, or a job on the virtual clock,
     * needs; without it the target does not load.
     */
    static ClockHost required(String what) throws LoadException {
        if (HOST.isEmpty()) {
            String message = what + " needs the coroutine bridge on the classpath: the project's "
                    + "build.gradle.kts applies the cs.coroutines plugin";
            throw new LoadException("ClockUnavailable", message);
        }
        return HOST.get();
    }

    /** Calls a suspend method and blocks until it returns, timing the call. */
    static Reflection.Timed invoke(Method method, Object instance, Object[] arguments)
            throws Reflection.UserCodeException {
        long start = System.nanoTime();
        Object value = call(method, instance, arguments, start);
        return new Reflection.Timed(value, System.nanoTime() - start);
    }

    /** Calls a suspend method and blocks until it returns, untimed. */
    static Object call(Method method, Object instance, Object[] arguments)
            throws Reflection.UserCodeException {
        return call(method, instance, arguments, System.nanoTime());
    }

    private static Object call(Method method, Object instance, Object[] arguments, long start)
            throws Reflection.UserCodeException {
        try {
            return HOST.orElseThrow().callBlocking(method, instance, arguments);
        } catch (Throwable error) {
            throw new Reflection.UserCodeException(error, System.nanoTime() - start);
        }
    }
}
