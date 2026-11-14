package bank;

import bank.accounts.Balances;

/** Accounts that hold a balance, keyed by account id. */
public class Bank {
    private final Balances balances = new Balances();

    public boolean createAccount(long timestamp, String accountId) {
        return balances.open(accountId);
    }

    public long deposit(long timestamp, String accountId, long amount) {
        if (!balances.has(accountId)) {
            return -1;
        }
        return balances.add(accountId, amount);
    }

    public long transfer(long timestamp, String sourceId, String targetId, long amount) {
        boolean known = balances.has(sourceId) && balances.has(targetId);
        if (!known || sourceId.equals(targetId) || balances.of(sourceId) < amount) {
            return -1;
        }
        balances.add(targetId, amount);
        return balances.add(sourceId, -amount);
    }
}
