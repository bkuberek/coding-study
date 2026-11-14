package probe;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

import org.junit.jupiter.api.Disabled;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

/**
 * One test per outcome of a suite job: a pass, a hang that the hang guard ends, an assertion
 * failure, an exit that ends the runner, an exception and output, then what only JUnit has: a
 * disabled test, a failed assumption and a parameterized test.
 */
class StatusesTest {
    private static final int EXIT_CODE = 3;

    @Test
    void passes() {
        assertEquals("pong", new Probe().ping());
    }

    @Test
    void hangs() {
        while (true) {
            Thread.onSpinWait();
        }
    }

    @Test
    void failsAnAssertion() {
        assertEquals("ping", new Probe().ping());
    }

    @Test
    void endsTheProcess() {
        System.exit(EXIT_CODE);
    }

    @Test
    void raises() {
        throw new IllegalStateException("conformance failure");
    }

    @Test
    void prints() {
        System.out.println("conformance output");
    }

    @Disabled("not ready")
    @Test
    void disabled() {
        assertTrue(false);
    }

    @Test
    void assumes() {
        assumeTrue(false, "no network");
    }

    @ParameterizedTest
    @ValueSource(ints = {1, 2})
    void counts(int count) {
        assertTrue(count > 0);
    }
}
