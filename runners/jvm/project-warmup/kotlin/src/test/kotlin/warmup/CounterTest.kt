package warmup

import kotlin.test.Test
import kotlin.test.assertEquals

/** Compiling a test resolves kotlin.test on JUnit 5 and JUnit's compile classpath. */
class CounterTest {
    @Test
    fun adds() {
        assertEquals(3, Counter().add(3))
    }
}
