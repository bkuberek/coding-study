import java.util.concurrent.locks.ReentrantLock;

public class Bank {
    private final long[] balances;
    private final ReentrantLock[] locks;

    public Bank(long[] balances) {
        this.balances = balances.clone();
        this.locks = new ReentrantLock[balances.length];
        for (int i = 0; i < locks.length; i++) {
            locks[i] = new ReentrantLock();
        }
    }

    public boolean transfer(int fromAccount, int toAccount, long amount) {
        if (!exists(fromAccount) || !exists(toAccount)) {
            return false;
        }
        ReentrantLock first = locks[Math.min(fromAccount, toAccount)];
        ReentrantLock second = locks[Math.max(fromAccount, toAccount)];
        first.lock();
        try {
            second.lock();
            try {
                if (balances[fromAccount] < amount) {
                    return false;
                }
                balances[fromAccount] -= amount;
                balances[toAccount] += amount;
                return true;
            } finally {
                second.unlock();
            }
        } finally {
            first.unlock();
        }
    }

    public long balance(int account) {
        if (!exists(account)) {
            return -1;
        }
        locks[account].lock();
        try {
            return balances[account];
        } finally {
            locks[account].unlock();
        }
    }

    public long total() {
        for (ReentrantLock lock : locks) {
            lock.lock();
        }
        try {
            long sum = 0;
            for (long balance : balances) {
                sum += balance;
            }
            return sum;
        } finally {
            for (int i = locks.length - 1; i >= 0; i--) {
                locks[i].unlock();
            }
        }
    }

    private boolean exists(int account) {
        return account >= 0 && account < balances.length;
    }
}
