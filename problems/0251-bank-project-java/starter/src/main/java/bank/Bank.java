package bank;

import java.util.HashMap;
import java.util.Map;

/**
 * A set of bank accounts that hold whole amounts of money and send money to one another: the
 * class that {@code cstudy submit} and the tests drive.
 */
public class Bank {
    private final Map<String, Account> accounts = new HashMap<>();

    /** Opens an account with balance 0; false when the id is taken. */
    public boolean createAccount(long timestamp, String accountId) {
        throw new UnsupportedOperationException("Not implemented");
    }

    /** Adds amount to the account and returns its new balance; -1 when there is no such account. */
    public long deposit(long timestamp, String accountId, long amount) {
        throw new UnsupportedOperationException("Not implemented");
    }

    /**
     * Moves amount from the source account to the target account and returns the source's new
     * balance; -1, changing nothing, when it cannot.
     */
    public long transfer(long timestamp, String sourceId, String targetId, long amount) {
        throw new UnsupportedOperationException("Not implemented");
    }
}
