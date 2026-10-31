package warmup;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

/** Compiling a test resolves JUnit's compile classpath, `apiguardian-api` among it. */
class CounterTest {
    @Test
    void adds() {
        assertEquals(3, new Counter().add(3));
    }
}
