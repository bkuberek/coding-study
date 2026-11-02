package warmup

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.currentTime
import kotlinx.coroutines.test.runTest

/**
 * Compiling a test resolves kotlin.test on JUnit 5, kotlinx-coroutines-test and JUnit's compile
 * classpath.
 */
@OptIn(ExperimentalCoroutinesApi::class)
class CounterTest {
    @Test
    fun adds() {
        assertEquals(3, Counter().add(3))
    }

    @Test
    fun addsOnTheVirtualClock() = runTest {
        assertEquals(3, Counter().addLater(3, 1000))
        assertEquals(1000, currentTime)
    }
}
