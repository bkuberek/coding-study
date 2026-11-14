package probe;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/** A class whose setup fails: reported once, under the class's own id, and never again. */
class BrokenSetupTest {
    @BeforeAll
    static void setUp() {
        throw new IllegalStateException("setup failure");
    }

    @Test
    void neverRuns() {
        assertEquals("pong", new Probe().ping());
    }
}
