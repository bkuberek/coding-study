package bank.schedule;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.PriorityQueue;

/**
 * Numbers booked transfers and hands them out by due time, ties in booking order.
 *
 * <p>A cancelled transfer stays in the queue and is dropped when it reaches the head, since a
 * {@link PriorityQueue} removes its head in O(log p) but any other element in O(p).
 */
public final class TransferScheduler {
    /** A booked transfer with its number, which orders bookings due at the same time. */
    private record Booking(long number, String id, ScheduledTransfer transfer) {
        long due() {
            return transfer.due();
        }
    }

    private static final Comparator<Booking> RUN_ORDER =
            Comparator.comparingLong(Booking::due).thenComparingLong(Booking::number);

    private final PriorityQueue<Booking> queue = new PriorityQueue<>(RUN_ORDER);
    private final Map<String, Booking> pending = new HashMap<>();
    private long booked;

    /** Queues {@code transfer} and returns its id, {@code transfer<k>} for the k-th booking. */
    public String book(ScheduledTransfer transfer) {
        booked++;
        Booking booking = new Booking(booked, "transfer" + booked, transfer);
        pending.put(booking.id(), booking);
        queue.add(booking);
        return booking.id();
    }

    /** The transfer with this id while it waits; empty once it ran, was skipped or cancelled. */
    public Optional<ScheduledTransfer> findPending(String transferId) {
        return Optional.ofNullable(pending.get(transferId)).map(Booking::transfer);
    }

    /** Cancels a pending transfer; false when no transfer with this id is pending. */
    public boolean cancel(String transferId) {
        return pending.remove(transferId) != null;
    }

    /** Removes and returns the pending transfers due by {@code now}, in the order they run. */
    public List<ScheduledTransfer> takeDue(long now) {
        List<ScheduledTransfer> due = new ArrayList<>();
        while (!queue.isEmpty() && queue.peek().due() <= now) {
            Booking next = queue.poll();
            if (pending.remove(next.id()) != null) {
                due.add(next.transfer());
            }
        }
        return due;
    }
}
