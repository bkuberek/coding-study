package bank.schedule

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue

class SchedulerTest {
    private val scheduler = Scheduler()

    private fun book(amount: Long, due: Long): String = scheduler.book(ScheduledTransfer("a", "b", amount, due))

    private fun amountsDueBy(now: Long): List<Long> = scheduler.takeDue(now).map { it.amount }

    @Test
    fun `numbers bookings from transfer1`() {
        book(amount = 1, due = 10)

        assertEquals("transfer2", book(amount = 2, due = 10))
    }

    @Test
    fun `hands out the earliest due first, not the first booked`() {
        book(amount = 1, due = 30)
        book(amount = 2, due = 20)

        assertEquals(listOf(2L, 1L), amountsDueBy(30))
    }

    @Test
    fun `hands out equal due times in booking order`() {
        book(amount = 1, due = 40)
        book(amount = 2, due = 40)
        book(amount = 3, due = 40)
        book(amount = 4, due = 33)

        assertEquals(listOf(4L, 1L, 2L, 3L), amountsDueBy(40))
    }

    @Test
    fun `hands out a transfer due exactly now`() {
        book(amount = 1, due = 20)

        assertEquals(listOf(1L), amountsDueBy(20))
    }

    @Test
    fun `keeps a transfer due later`() {
        book(amount = 1, due = 20)

        assertEquals(emptyList<Long>(), amountsDueBy(19))
    }

    @Test
    fun `hands out each transfer once`() {
        book(amount = 1, due = 20)
        scheduler.takeDue(20)

        assertEquals(emptyList<Long>(), amountsDueBy(30))
    }

    @Test
    fun `cancels a pending transfer`() {
        assertTrue(scheduler.cancel(book(amount = 1, due = 20)))
    }

    @Test
    fun `cannot cancel a transfer twice`() {
        val id = book(amount = 1, due = 20)
        scheduler.cancel(id)

        assertFalse(scheduler.cancel(id))
    }

    @Test
    fun `never hands out a cancelled transfer`() {
        scheduler.cancel(book(amount = 1, due = 20))

        assertEquals(emptyList<Long>(), amountsDueBy(20))
    }

    @Test
    fun `cannot cancel a transfer handed out to run`() {
        val id = book(amount = 1, due = 20)
        scheduler.takeDue(20)

        assertFalse(scheduler.cancel(id))
    }

    @Test
    fun `no longer lists a transfer handed out to run as pending`() {
        val id = book(amount = 1, due = 20)
        scheduler.takeDue(20)

        assertNull(scheduler.pending(id))
    }

    @Test
    fun `knows no transfer by an id it never gave`() {
        assertNull(scheduler.pending("transfer1"))
    }
}
