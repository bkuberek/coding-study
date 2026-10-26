public class Bank {
    private final long[] balances;
    private final Object[] locks;

    public Bank(long[] balances) {
        this.balances = balances.clone();
        this.locks = new Object[balances.length];
        for (int i = 0; i < locks.length; i++) {
            locks[i] = new Object();
        }
    }

    public boolean transfer(int fromAccount, int toAccount, long amount) {
        if (!exists(fromAccount) || !exists(toAccount)) {
            return false;
        }
        synchronized (locks[fromAccount]) {
            synchronized (locks[toAccount]) {
                if (balances[fromAccount] < amount) {
                    return false;
                }
                balances[fromAccount] -= amount;
                balances[toAccount] += amount;
                return true;
            }
        }
    }

    public long balance(int account) {
        if (!exists(account)) {
            return -1;
        }
        synchronized (locks[account]) {
            return balances[account];
        }
    }

    public long total() {
        return sumFrom(0);
    }

    private long sumFrom(int account) {
        if (account == balances.length) {
            long sum = 0;
            for (long balance : balances) {
                sum += balance;
            }
            return sum;
        }
        synchronized (locks[account]) {
            return sumFrom(account + 1);
        }
    }

    private boolean exists(int account) {
        return account >= 0 && account < balances.length;
    }
}
