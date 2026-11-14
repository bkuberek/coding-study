package bank.schedule

import java.util.PriorityQueue

/**
 * Money booked to move from [sourceId] to [targetId] at time [due]. The ids are those given
 * at booking time; a merge may hand them to another account later.
 */
internal data class ScheduledTransfer(val sourceId: String, val targetId: String, val amount: Long, val due: Long)

/**
 * Numbers booked transfers and hands them out by due time, ties in booking order. It knows
 * account ids, never accounts: what running a transfer means is the bank's business.
 *
 * [pending] holds exactly the bookings that may still run. Taking a booking to run, or
 * cancelling it, removes it from there; a cancelled booking stays in the queue and is dropped
 * when it reaches the head, since a heap removes only its head cheaply.
 */
internal class Scheduler {
    private var booked = 0
    private val pending = HashMap<String, Booking>()
    private val queue = PriorityQueue(compareBy<Booking> { it.transfer.due }.thenBy { it.number })

    /** Queues [transfer] and returns its id, `"transfer<k>"` for the k-th booking. */
    fun book(transfer: ScheduledTransfer): String {
        val booking = Booking(++booked, transfer)
        pending[booking.id] = booking
        queue.add(booking)
        return booking.id
    }

    /** The transfer booked as [id] while it still waits to run. */
    fun pending(id: String): ScheduledTransfer? = pending[id]?.transfer

    /** Withdraws the transfer booked as [id], so it never runs; false when it is not pending. */
    fun cancel(id: String): Boolean = pending.remove(id) != null

    /** Takes the pending transfers due at or before [now] out of the schedule, in run order: by due time, ties in booking order. */
    fun takeDue(now: Long): List<ScheduledTransfer> = buildList {
        while (queue.peek()?.let { it.transfer.due <= now } == true) {
            val booking = queue.poll()
            if (pending.remove(booking.id) != null) {
                add(booking.transfer)
            }
        }
    }

    private class Booking(val number: Int, val transfer: ScheduledTransfer) {
        val id = "transfer$number"
    }
}
