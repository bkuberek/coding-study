package cs.runner;

/** A loaded job target that turns each case into a ready-to-run call. */
interface Target<C> {
    /** Decodes fresh inputs for {@code testCase}; a malformed input is a bad request. */
    PreparedCase prepare(C testCase);

    /**
     * Bench mode: decodes fresh inputs now; the call runs user code, untimed and unserialized.
     * Throws when user code already fails while preparing (a throwing no-arg constructor).
     */
    RawCall prepareCall(C testCase) throws Reflection.UserCodeException;

    /** The package of the target's classes, which keeps stack traces to user frames. */
    String userPackage();

    /** A case with its inputs decoded; running it calls user code. */
    interface PreparedCase {
        CaseResult run();
    }

    /** One call of user code (a whole operation sequence for class kinds). */
    interface RawCall {
        Object call() throws Reflection.UserCodeException;
    }
}
