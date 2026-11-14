package bank;

/** One bank account. Grow it as the levels add rules, or replace it. */
final class Account {
    private final String id;
    private long balance;

    Account(String id) {
        this.id = id;
    }

    String id() {
        return id;
    }

    long balance() {
        return balance;
    }
}
