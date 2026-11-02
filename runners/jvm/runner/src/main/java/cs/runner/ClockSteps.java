package cs.runner;

/**
 * The operations of one case on the virtual clock, decoded, and the record of their results,
 * which the runner keeps: a {@link ClockHost} runs the steps and hands each result back.
 */
public interface ClockSteps {
    /** How many operations the case has; operation 0 constructs the instance. */
    int size();

    /** Operation {@code index}, decoded with fresh arguments, right before it runs. */
    ClockStep step(int index);

    /**
     * Records what operation {@code index} produced: the new instance for the constructor, the
     * call's result, the joined task's result, the virtual milliseconds for {@code @now}, null
     * for {@code @advance} and {@code @spawn}. False when the result is not a valid output, which
     * the runner has recorded: the case ends there.
     */
    boolean returned(int index, Object value);
}
