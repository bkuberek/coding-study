package bank;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Stream;

/** Every account by id, merged-away ones included, and who holds an id now. */
final class Ledger {
    private final Map<String, Account> accounts = new HashMap<>();

    /** Opens an account; false when the id is taken, even by a merged-away account. */
    boolean open(String accountId, long timestamp) {
        return accounts.putIfAbsent(accountId, new Account(accountId, timestamp)) == null;
    }

    /** The account with this id, open or merged away. */
    Optional<Account> find(String accountId) {
        return Optional.ofNullable(accounts.get(accountId));
    }

    Optional<Account> findOpen(String accountId) {
        return find(accountId).filter(Account::isOpen);
    }

    Stream<Account> openAccounts() {
        return accounts.values().stream().filter(Account::isOpen);
    }

    /**
     * Folds {@code otherId} into {@code accountId}; false, changing nothing, when the ids are equal
     * or either account is not open.
     */
    boolean merge(long timestamp, String accountId, String otherId) {
        Optional<Account> kept = findOpen(accountId);
        Optional<Account> absorbed = findOpen(otherId);
        if (kept.isEmpty() || absorbed.isEmpty() || kept.get() == absorbed.get()) {
            return false;
        }
        kept.get().absorb(absorbed.get(), timestamp);
        return true;
    }

    /** The open account that holds {@code accountId} now; the id must have been opened. */
    Account holderOf(String accountId) {
        return accounts.get(accountId).holder();
    }
}
