package bank.schedule;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import org.junit.jupiter.api.Test;

class TransferSchedulerTest {
    private static ScheduledTransfer due(long due, long amount) {
        return new ScheduledTransfer("a", "b", amount, due);
    }

    @Test
    void numbersBookingsFromOne() {
        TransferScheduler scheduler = new TransferScheduler();
        scheduler.book(due(10, 1));

        assertEquals("transfer2", scheduler.book(due(5, 2)));
    }

    @Test
    void handsOutTransfersInDueTimeOrder() {
        TransferScheduler scheduler = new TransferScheduler();
        scheduler.book(due(30, 1));
        scheduler.book(due(10, 2));
        scheduler.book(due(20, 3));

        assertEquals(List.of(due(10, 2), due(20, 3), due(30, 1)), scheduler.takeDue(30));
    }

    @Test
    void handsOutTransfersDueTogetherInBookingOrder() {
        TransferScheduler scheduler = new TransferScheduler();
        scheduler.book(due(40, 1));
        scheduler.book(due(40, 2));
        scheduler.book(due(40, 3));
        scheduler.book(due(35, 4));

        assertEquals(
                List.of(due(35, 4), due(40, 1), due(40, 2), due(40, 3)), scheduler.takeDue(40));
    }

    @Test
    void takesATransferDueExactlyNow() {
        TransferScheduler scheduler = new TransferScheduler();
        scheduler.book(due(10, 1));

        assertEquals(List.of(due(10, 1)), scheduler.takeDue(10));
    }

    @Test
    void leavesATransferDueLater() {
        TransferScheduler scheduler = new TransferScheduler();
        scheduler.book(due(10, 1));

        assertEquals(List.of(), scheduler.takeDue(9));
    }

    @Test
    void dropsACancelledTransfer() {
        TransferScheduler scheduler = new TransferScheduler();
        String cancelled = scheduler.book(due(10, 1));
        scheduler.book(due(10, 2));
        scheduler.cancel(cancelled);

        assertEquals(List.of(due(10, 2)), scheduler.takeDue(10));
    }

    @Test
    void cancelsATransferOnlyOnce() {
        TransferScheduler scheduler = new TransferScheduler();
        String id = scheduler.book(due(10, 1));
        scheduler.cancel(id);

        assertFalse(scheduler.cancel(id));
    }

    @Test
    void forgetsATransferHandedOut() {
        TransferScheduler scheduler = new TransferScheduler();
        String id = scheduler.book(due(10, 1));
        scheduler.takeDue(10);

        assertTrue(scheduler.findPending(id).isEmpty());
    }
}
