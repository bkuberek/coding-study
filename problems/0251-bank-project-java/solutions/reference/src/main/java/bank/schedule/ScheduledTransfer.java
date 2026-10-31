package bank.schedule;

/**
 * Money booked to move from {@code sourceId} to {@code targetId} at time {@code due}.
 *
 * <p>The ids are those given at booking time; a merge may hand them to another account.
 */
public record ScheduledTransfer(String sourceId, String targetId, long amount, long due) {}
