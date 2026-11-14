package bank.accounts;

import java.util.HashMap;
import java.util.Map;

/** The balance of every account, by id. */
public class Balances {
    private final Map<String, Long> balances = new HashMap<>();

    public boolean open(String accountId) {
        return balances.putIfAbsent(accountId, 0L) == null;
    }

    public boolean has(String accountId) {
        return balances.containsKey(accountId);
    }

    public long of(String accountId) {
        return balances.get(accountId);
    }

    public long add(String accountId, long amount) {
        return balances.merge(accountId, amount, Long::sum);
    }
}
