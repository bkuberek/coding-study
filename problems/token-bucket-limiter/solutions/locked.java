import java.util.concurrent.locks.ReentrantLock;

public class TokenBucket {
    private final long capacity;
    private final long refillPerSecond;
    private final ReentrantLock lock = new ReentrantLock();
    private long stored;
    private long lastRefill;

    public TokenBucket(long capacity, long refillPerSecond) {
        this.capacity = capacity;
        this.refillPerSecond = refillPerSecond;
        this.stored = capacity;
    }

    public boolean tryAcquire(long timestamp, long tokens) {
        lock.lock();
        try {
            refill(timestamp);
            if (stored < tokens) {
                return false;
            }
            stored -= tokens;
            return true;
        } finally {
            lock.unlock();
        }
    }

    public long available(long timestamp) {
        lock.lock();
        try {
            refill(timestamp);
            return stored;
        } finally {
            lock.unlock();
        }
    }

    private void refill(long timestamp) {
        if (timestamp <= lastRefill) {
            return;
        }
        stored = Math.min(capacity, stored + (timestamp - lastRefill) * refillPerSecond);
        lastRefill = timestamp;
    }
}
