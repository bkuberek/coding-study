import java.util.ArrayDeque;
import java.util.concurrent.locks.Condition;
import java.util.concurrent.locks.ReentrantLock;

public class ConcurrencyLimiter {
    private static final class Waiter {
        final Condition granted;
        boolean hasPermit;

        Waiter(Condition granted) {
            this.granted = granted;
        }
    }

    private final ReentrantLock lock = new ReentrantLock();
    private final ArrayDeque<Waiter> waiters = new ArrayDeque<>();
    private int permits;

    public ConcurrencyLimiter(int limit) {
        this.permits = limit;
    }

    public void acquire() throws InterruptedException {
        lock.lock();
        try {
            if (permits > 0) {
                permits--;
                return;
            }
            Waiter me = new Waiter(lock.newCondition());
            waiters.addLast(me);
            try {
                while (!me.hasPermit) {
                    me.granted.await();
                }
            } catch (InterruptedException e) {
                if (me.hasPermit) {
                    passOn();
                } else {
                    waiters.remove(me);
                }
                throw e;
            }
        } finally {
            lock.unlock();
        }
    }

    public boolean tryAcquire() {
        lock.lock();
        try {
            if (permits == 0) {
                return false;
            }
            permits--;
            return true;
        } finally {
            lock.unlock();
        }
    }

    public void release() {
        lock.lock();
        try {
            passOn();
        } finally {
            lock.unlock();
        }
    }

    public int available() {
        lock.lock();
        try {
            return permits;
        } finally {
            lock.unlock();
        }
    }

    private void passOn() {
        Waiter next = waiters.pollFirst();
        if (next == null) {
            permits++;
            return;
        }
        next.hasPermit = true;
        next.granted.signal();
    }
}
