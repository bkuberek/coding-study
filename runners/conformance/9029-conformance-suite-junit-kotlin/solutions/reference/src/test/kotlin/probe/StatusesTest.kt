package probe

import org.junit.jupiter.api.Assumptions.assumeTrue
import org.junit.jupiter.api.Disabled
import org.junit.jupiter.params.ParameterizedTest
import org.junit.jupiter.params.provider.ValueSource
import kotlin.system.exitProcess
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

/**
 * One test per outcome of a suite job: a pass, a hang that the hang guard ends, an assertion
 * failure, an exit that ends the runner, an exception and output, then what only JUnit has: a
 * disabled test, a failed assumption and a parameterized test.
 */
class StatusesTest {
    @Test
    fun passes() {
        assertEquals("pong", Probe().ping())
    }

    @Test
    fun hangs() {
        while (true) {
            Thread.onSpinWait()
        }
    }

    @Test
    fun failsAnAssertion() {
        assertEquals("ping", Probe().ping())
    }

    @Test
    fun endsTheProcess() {
        exitProcess(EXIT_CODE)
    }

    @Test
    fun raises() {
        error("conformance failure")
    }

    @Test
    fun prints() {
        println("conformance output")
    }

    @Disabled("not ready")
    @Test
    fun disabled() {
        assertTrue(false)
    }

    @Test
    fun assumes() {
        assumeTrue(false, "no network")
    }

    @ParameterizedTest
    @ValueSource(ints = [1, 2])
    fun counts(count: Int) {
        assertTrue(count > 0)
    }

    private companion object {
        const val EXIT_CODE = 3
    }
}
