public class Bank {
    private final long[] balances;

    public Bank(long[] balances) {
        this.balances = balances.clone();
    }

    public synchronized boolean transfer(int fromAccount, int toAccount, long amount) {
        if (!exists(fromAccount) || !exists(toAccount) || balances[fromAccount] < amount) {
            return false;
        }
        balances[fromAccount] -= amount;
        balances[toAccount] += amount;
        return true;
    }

    public synchronized long balance(int account) {
        return exists(account) ? balances[account] : -1;
    }

    public synchronized long total() {
        long sum = 0;
        for (long balance : balances) {
            sum += balance;
        }
        return sum;
    }

    private boolean exists(int account) {
        return account >= 0 && account < balances.length;
    }
}
