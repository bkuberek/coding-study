package cs.runner;

import java.lang.reflect.Constructor;
import java.lang.reflect.Method;

/**
 * One operation of a case on the virtual clock, as {@link ClockHost} runs it
 * (docs/specs/problem-format.md#semantics-of-a-case-on-the-virtual-clock): every operation
 * settles before the next one.
 */
public sealed interface ClockStep {
    /** Operation 0: constructs the instance that every later call is made on. */
    record Construct(Constructor<?> constructor, Object[] arguments) implements ClockStep {
    }

    /**
     * Calls {@code method} on the instance and waits for its result while the clock moves.
     *
     * @param suspending a {@code suspend} method, whose last JVM parameter is the continuation
     */
    record Call(Method method, Object[] arguments, boolean suspending) implements ClockStep {
    }

    /** {@code @advance}: the clock moves {@code milliseconds} forward. */
    record Advance(long milliseconds) implements ClockStep {
    }

    /** {@code @spawn}: starts the call as the task {@code task} without waiting for it. */
    record Spawn(String task, Call call) implements ClockStep {
    }

    /** {@code @join}: waits for the task {@code task}, whose error or result is this step's. */
    record Join(String task) implements ClockStep {
    }

    /** {@code @now}: the virtual milliseconds since the case started. */
    record Now() implements ClockStep {
    }
}
