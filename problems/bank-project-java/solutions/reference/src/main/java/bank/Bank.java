package bank;

import bank.schedule.ScheduledTransfer;
import bank.schedule.TransferScheduler;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;

/**
 * A set of bank accounts that hold whole amounts of money and send money to one another: the
 * class that {@code cstudy submit} and the tests drive.
 *
 * <p>Every public method first runs the scheduled transfers that fell due by its timestamp, so it
 * sees the bank as it is at that moment. Only this class knows the grader's sentinels; the classes
 * it delegates to answer with {@link Optional} and {@code boolean}.
 */
public final class Bank {
    private static final long FAILED = -1;
    private static final String NOT_BOOKED = "";

    /** Larger totals sent first, equal totals by id. */
    private static final Comparator<Account> BY_SPENDING =
            Comparator.comparingLong(Account::sent).reversed().thenComparing(Account::id);

    private final Ledger ledger = new Ledger();
    private final TransferScheduler scheduler = new TransferScheduler();

    public boolean createAccount(long timestamp, String accountId) {
        settle(timestamp);
        return ledger.open(accountId, timestamp);
    }

    public long deposit(long timestamp, String accountId, long amount) {
        settle(timestamp);
        return ledger.findOpen(accountId)
                .map(account -> account.deposit(timestamp, amount))
                .orElse(FAILED);
    }

    public long transfer(long timestamp, String sourceId, String targetId, long amount) {
        settle(timestamp);
        Optional<Account> source = ledger.findOpen(sourceId);
        Optional<Account> target = ledger.findOpen(targetId);
        if (source.isEmpty() || target.isEmpty() || !source.get().canSend(target.get(), amount)) {
            return FAILED;
        }
        return source.get().send(target.get(), timestamp, amount);
    }

    public List<String> topSpenders(long timestamp, int n) {
        settle(timestamp);
        return ledger.openAccounts()
                .sorted(BY_SPENDING)
                .limit(n)
                .map(account -> account.id() + "(" + account.sent() + ")")
                .toList();
    }

    public String scheduleTransfer(
            long timestamp, String sourceId, String targetId, long amount, long delay) {
        settle(timestamp);
        Optional<Account> source = ledger.findOpen(sourceId);
        Optional<Account> target = ledger.findOpen(targetId);
        if (source.isEmpty() || target.isEmpty() || source.get() == target.get()) {
            return NOT_BOOKED;
        }
        return scheduler.book(new ScheduledTransfer(sourceId, targetId, amount, timestamp + delay));
    }

    public boolean cancelTransfer(long timestamp, String accountId, String transferId) {
        settle(timestamp);
        Optional<ScheduledTransfer> transfer = scheduler.findPending(transferId);
        if (transfer.isEmpty()) {
            return false;
        }
        Account sender = ledger.holderOf(transfer.get().sourceId());
        return sender.id().equals(accountId) && scheduler.cancel(transferId);
    }

    public boolean mergeAccounts(long timestamp, String accountId, String otherId) {
        settle(timestamp);
        return ledger.merge(timestamp, accountId, otherId);
    }

    public long getBalance(long timestamp, String accountId, long timeAt) {
        settle(timestamp);
        Optional<Account> account = ledger.find(accountId);
        if (account.isEmpty()) {
            return FAILED;
        }
        return account.get().balanceAt(timeAt).orElse(FAILED);
    }

    /** Runs every scheduled transfer due by {@code now}, each at its own due time. */
    private void settle(long now) {
        for (ScheduledTransfer transfer : scheduler.takeDue(now)) {
            Account source = ledger.holderOf(transfer.sourceId());
            Account target = ledger.holderOf(transfer.targetId());
            if (source.canSend(target, transfer.amount())) {
                source.send(target, transfer.due(), transfer.amount());
            }
        }
    }
}
