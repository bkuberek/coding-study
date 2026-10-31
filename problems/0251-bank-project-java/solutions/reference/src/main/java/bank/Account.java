package bank;

import java.util.OptionalLong;

/**
 * One bank account: its balance, the money it sent, its balance history and, once merged away,
 * where it went. The rules that change those numbers live here.
 */
final class Account {
    /** Where a merged-away account went, and when. */
    private record Merge(Account into, long at) {}

    private final String id;
    private final BalanceHistory history = new BalanceHistory();
    private long balance;
    private long sent;
    private Merge merge;

    Account(String id, long createdAt) {
        this.id = id;
        history.record(createdAt, balance);
    }

    String id() {
        return id;
    }

    long balance() {
        return balance;
    }

    /** The total of every transfer this account sent, and of the accounts it absorbed. */
    long sent() {
        return sent;
    }

    boolean isOpen() {
        return merge == null;
    }

    long deposit(long timestamp, long amount) {
        return changeBalance(timestamp, amount);
    }

    boolean canSend(Account target, long amount) {
        return target != this && balance >= amount;
    }

    /** Moves {@code amount} to {@code target} and returns this account's new balance. */
    long send(Account target, long timestamp, long amount) {
        target.changeBalance(timestamp, amount);
        sent += amount;
        return changeBalance(timestamp, -amount);
    }

    /** Adds {@code other}'s balance and total sent to this account and closes {@code other}. */
    void absorb(Account other, long timestamp) {
        changeBalance(timestamp, other.balance);
        sent += other.sent;
        other.merge = new Merge(this, timestamp);
    }

    /** The open account that holds this one now, following its merges. */
    Account holder() {
        return merge == null ? this : merge.into().holder();
    }

    /** The balance at {@code moment}; empty when the account did not exist then. */
    OptionalLong balanceAt(long moment) {
        if (merge != null && moment >= merge.at()) {
            return OptionalLong.empty();
        }
        return history.at(moment);
    }

    private long changeBalance(long timestamp, long delta) {
        balance += delta;
        history.record(timestamp, balance);
        return balance;
    }
}
