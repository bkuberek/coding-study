public class Bank {
    private final long[] balances;

    public Bank(long[] balances) {
        this.balances = balances.clone();
    }

    public boolean transfer(int fromAccount, int toAccount, long amount) {
        if (!exists(fromAccount) || !exists(toAccount) || balances[fromAccount] < amount) {
            return false;
        }
        balances[fromAccount] -= amount;
        balances[toAccount] += amount;
        return true;
    }

    public long balance(int account) {
        return exists(account) ? balances[account] : -1;
    }

    public long total() {
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
