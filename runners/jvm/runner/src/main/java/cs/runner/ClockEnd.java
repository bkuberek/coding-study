package cs.runner;

/** How a case on the virtual clock ended, as {@link ClockHost#run} reports it. */
public sealed interface ClockEnd {
    /** Every operation ran and settled, and no coroutine of the case is left. */
    record Finished() implements ClockEnd {
    }

    /**
     * Operation {@code index} threw {@code error}, or a coroutine of the case failed with it while
     * that operation ran.
     */
    record Failed(int index, Throwable error) implements ClockEnd {
    }

    /** {@link ClockSteps#returned} refused the result of operation {@code index}. */
    record Refused(int index) implements ClockEnd {
    }

    /**
     * Operation {@code index} waited while no coroutine could run and nothing was due on the
     * clock, which read {@code milliseconds}.
     */
    record Deadlocked(int index, long milliseconds) implements ClockEnd {
    }

    /**
     * Every operation ran, but coroutines of the case were still active once nothing was due on
     * the clock, which read {@code milliseconds}; {@code index} is the last operation.
     */
    record LeftActive(int index, long milliseconds) implements ClockEnd {
    }
}
