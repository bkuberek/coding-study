import java.util.*;

public class Bank {
    private static final class Account {
        final String id;
        final long createdAt;
        long balance;
        long outgoing;
        Long closedAt;
        /** Time to balance after the last change at that time: the account's balance history. */
        private final TreeMap<Long, Long> history = new TreeMap<>();

        Account(String id, long createdAt) {
            this.id = id;
            this.createdAt = createdAt;
            changeBalance(createdAt, 0);
        }

        long changeBalance(long timestamp, long delta) {
            balance += delta;
            history.put(timestamp, balance);
            return balance;
        }

        long balanceAt(long moment) {
            if (moment < createdAt || (closedAt != null && moment >= closedAt)) {
                return -1;
            }
            return history.floorEntry(moment).getValue();
        }

        boolean isOpen() {
            return closedAt == null;
        }

        boolean canSend(Account target, long amount) {
            return this != target && balance >= amount;
        }

        long send(Account target, long timestamp, long amount) {
            target.changeBalance(timestamp, amount);
            outgoing += amount;
            return changeBalance(timestamp, -amount);
        }
    }

    private static final class ScheduledTransfer {
        final String id;
        final long number;
        final String sourceId;
        final String targetId;
        final long amount;
        final long due;
        boolean pending = true;

        ScheduledTransfer(long number, String sourceId, String targetId, long amount, long due) {
            this.id = "transfer" + number;
            this.number = number;
            this.sourceId = sourceId;
            this.targetId = targetId;
            this.amount = amount;
            this.due = due;
        }
    }

    private static final Comparator<Account> BY_SPENDING =
            Comparator.comparingLong((Account account) -> account.outgoing).reversed()
                    .thenComparing(account -> account.id);

    private static final Comparator<ScheduledTransfer> BY_DUE_TIME =
            Comparator.comparingLong((ScheduledTransfer scheduled) -> scheduled.due)
                    .thenComparingLong(scheduled -> scheduled.number);

    private final Map<String, Account> accounts = new HashMap<>();
    private final Map<String, String> mergedInto = new HashMap<>();
    private final Map<String, ScheduledTransfer> transfers = new HashMap<>();
    /** Earliest due first, ties in scheduling order. A cancelled transfer stays here until it reaches the head. */
    private final PriorityQueue<ScheduledTransfer> due = new PriorityQueue<>(BY_DUE_TIME);

    public Bank() {
    }

    // Level 1
    public boolean createAccount(long timestamp, String accountId) {
        settle(timestamp);
        if (accounts.containsKey(accountId)) {
            return false;
        }
        accounts.put(accountId, new Account(accountId, timestamp));
        return true;
    }

    public long deposit(long timestamp, String accountId, long amount) {
        settle(timestamp);
        Account account = open(accountId);
        return account == null ? -1 : account.changeBalance(timestamp, amount);
    }

    public long transfer(long timestamp, String sourceId, String targetId, long amount) {
        settle(timestamp);
        Account source = open(sourceId);
        Account target = open(targetId);
        if (source == null || target == null || !source.canSend(target, amount)) {
            return -1;
        }
        return source.send(target, timestamp, amount);
    }

    // Level 2
    public List<String> topSpenders(long timestamp, int n) {
        settle(timestamp);
        return accounts.values().stream()
                .filter(Account::isOpen)
                .sorted(BY_SPENDING)
                .limit(n)
                .map(account -> account.id + "(" + account.outgoing + ")")
                .toList();
    }

    // Level 3
    public String scheduleTransfer(long timestamp, String sourceId, String targetId, long amount, long delay) {
        settle(timestamp);
        Account source = open(sourceId);
        Account target = open(targetId);
        if (source == null || target == null || source == target) {
            return "";
        }
        ScheduledTransfer scheduled =
                new ScheduledTransfer(transfers.size() + 1, sourceId, targetId, amount, timestamp + delay);
        transfers.put(scheduled.id, scheduled);
        due.add(scheduled);
        return scheduled.id;
    }

    public boolean cancelTransfer(long timestamp, String accountId, String transferId) {
        settle(timestamp);
        ScheduledTransfer scheduled = transfers.get(transferId);
        if (open(accountId) == null || scheduled == null || !scheduled.pending) {
            return false;
        }
        if (!owner(scheduled.sourceId).equals(accountId)) {
            return false;
        }
        scheduled.pending = false;
        return true;
    }

    // Level 4
    public boolean mergeAccounts(long timestamp, String accountId, String otherId) {
        settle(timestamp);
        Account account = open(accountId);
        Account other = open(otherId);
        if (account == null || other == null || account == other) {
            return false;
        }
        account.changeBalance(timestamp, other.balance);
        account.outgoing += other.outgoing;
        other.closedAt = timestamp;
        mergedInto.put(otherId, accountId);
        return true;
    }

    public long getBalance(long timestamp, String accountId, long timeAt) {
        settle(timestamp);
        Account account = accounts.get(accountId);
        return account == null ? -1 : account.balanceAt(timeAt);
    }

    private Account open(String accountId) {
        Account account = accounts.get(accountId);
        return account != null && account.isOpen() ? account : null;
    }

    /** The open account that now holds {@code accountId}, following merges. */
    private String owner(String accountId) {
        String current = accountId;
        while (mergedInto.containsKey(current)) {
            current = mergedInto.get(current);
        }
        return current;
    }

    /** Run every scheduled transfer due at or before {@code timestamp}, each at its own due time. */
    private void settle(long timestamp) {
        while (!due.isEmpty() && due.peek().due <= timestamp) {
            ScheduledTransfer scheduled = due.poll();
            if (!scheduled.pending) {
                continue;
            }
            scheduled.pending = false;
            Account source = accounts.get(owner(scheduled.sourceId));
            Account target = accounts.get(owner(scheduled.targetId));
            if (source.canSend(target, scheduled.amount)) {
                source.send(target, scheduled.due, scheduled.amount);
            }
        }
    }
}
