public class TokenBucket {
    private final long capacity;
    private final long refillPerSecond;
    private long stored;
    private long lastRefill;

    public TokenBucket(long capacity, long refillPerSecond) {
        this.capacity = capacity;
        this.refillPerSecond = refillPerSecond;
        this.stored = capacity;
    }

    public boolean tryAcquire(long timestamp, long tokens) {
        refill(timestamp);
        if (stored < tokens) {
            return false;
        }
        stored -= tokens;
        return true;
    }

    public long available(long timestamp) {
        refill(timestamp);
        return stored;
    }

    private void refill(long timestamp) {
        if (timestamp <= lastRefill) {
            return;
        }
        stored = Math.min(capacity, stored + (timestamp - lastRefill) * refillPerSecond);
        lastRefill = timestamp;
    }
}
