package probe

import org.junit.jupiter.api.BeforeAll
import kotlin.test.Test
import kotlin.test.assertEquals

/** A class whose setup fails: reported once, under the class's own id, and never again. */
class BrokenSetupTest {
    @Test
    fun neverRuns() {
        assertEquals("pong", Probe().ping())
    }

    companion object {
        @JvmStatic
        @BeforeAll
        fun setUp() {
            error("setup failure")
        }
    }
}
