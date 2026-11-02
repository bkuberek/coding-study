package cs.runner;

import java.lang.reflect.Method;

/**
 * The virtual clock of a Kotlin project and the caller of its {@code suspend} methods
 * (docs/specs/runners.md#virtual-clock-and-stress-in-project-jobs).
 *
 * <p>The runner finds it with {@link java.util.ServiceLoader}: the module {@code cs.coroutines}
 * implements it on a {@code kotlinx-coroutines-test} scheduler and is on the classpath of a
 * project that applies the {@code cs.coroutines} plugin, as {@code cs.suite} is on a project's
 * test runtime classpath. {@code hello} lists the {@code clock} feature only when one is there.
 */
public interface ClockHost {
    /**
     * Runs the steps of one case, in order, on a fresh virtual clock that starts at 0, from the
     * constructor on, and returns how the case ended. The case's coroutines run on the calling
     * thread; whatever the case leaves behind is cancelled before this returns.
     */
    ClockEnd run(ClockSteps steps);

    /**
     * Calls a {@code suspend} method on the real clock and blocks the calling thread until it
     * returns: a stress worker's call, or a call outside the virtual clock. Throws what the
     * method throws.
     */
    Object callBlocking(Method method, Object instance, Object[] arguments) throws Throwable;
}
