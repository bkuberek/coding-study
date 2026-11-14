package bank

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

class BalanceHistoryTest {
    private val history = BalanceHistory().apply {
        record(10, 0)
        record(20, 70)
        record(30, 45)
    }

    @Test
    fun `has no balance before the first change`() {
        assertNull(history.at(9))
    }

    @Test
    fun `answers at the exact time of a change`() {
        assertEquals(70L, history.at(20))
    }

    @Test
    fun `answers between changes with the earlier one`() {
        assertEquals(70L, history.at(29))
    }

    @Test
    fun `answers after the last change with it`() {
        assertEquals(45L, history.at(1_000))
    }

    @Test
    fun `keeps the last of several changes at one moment`() {
        history.record(40, 60)
        history.record(40, 15)

        assertEquals(15L, history.at(40))
    }
}
