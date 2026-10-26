import java.util.*;

public class BankingSystem {
    private static final long CASHBACK_DELAY = 86_400_000L;
    private static final long CASHBACK_PERCENT = 2;

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
    }

    private static final class Payment {
        final String id;
        final String accountId;
        final long cashback;
        final long due;
        boolean received;

        Payment(String id, String accountId, long cashback, long due) {
            this.id = id;
            this.accountId = accountId;
            this.cashback = cashback;
            this.due = due;
        }
    }

    private static final Comparator<Account> BY_SPENDING =
            Comparator.comparingLong((Account account) -> account.outgoing).reversed()
                    .thenComparing(account -> account.id);

    private final Map<String, Account> accounts = new HashMap<>();
    private final Map<String, String> mergedInto = new HashMap<>();
    private final Map<String, Payment> payments = new HashMap<>();
    /** The delay is constant and timestamps increase, so cashbacks fall due in payment order. */
    private final Deque<Payment> pending = new ArrayDeque<>();

    public BankingSystem() {
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
        if (source == null || target == null || source == target || source.balance < amount) {
            return -1;
        }
        target.changeBalance(timestamp, amount);
        source.outgoing += amount;
        return source.changeBalance(timestamp, -amount);
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
    public String pay(long timestamp, String accountId, long amount) {
        settle(timestamp);
        Account account = open(accountId);
        if (account == null || account.balance < amount) {
            return "";
        }
        account.changeBalance(timestamp, -amount);
        account.outgoing += amount;
        Payment payment = new Payment(
                "payment" + (payments.size() + 1),
                accountId,
                amount * CASHBACK_PERCENT / 100,
                timestamp + CASHBACK_DELAY);
        payments.put(payment.id, payment);
        pending.addLast(payment);
        return payment.id;
    }

    public String paymentStatus(long timestamp, String accountId, String paymentId) {
        settle(timestamp);
        Payment payment = payments.get(paymentId);
        if (open(accountId) == null || payment == null || !owner(payment.accountId).equals(accountId)) {
            return "";
        }
        return payment.received ? "CASHBACK_RECEIVED" : "IN_PROGRESS";
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

    /** Credit every cashback due at or before {@code timestamp}, at its own due time. */
    private void settle(long timestamp) {
        while (!pending.isEmpty() && pending.peekFirst().due <= timestamp) {
            Payment payment = pending.pollFirst();
            accounts.get(owner(payment.accountId)).changeBalance(payment.due, payment.cashback);
            payment.received = true;
        }
    }
}
