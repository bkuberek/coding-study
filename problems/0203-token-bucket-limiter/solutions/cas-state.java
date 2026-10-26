import java.util.concurrent.atomic.AtomicReference;

public class TokenBucket {
    private record State(long stored, long lastRefill) {}

    private final long capacity;
    private final long refillPerSecond;
    private final AtomicReference<State> state;

    public TokenBucket(long capacity, long refillPerSecond) {
        this.capacity = capacity;
        this.refillPerSecond = refillPerSecond;
        this.state = new AtomicReference<>(new State(capacity, 0));
    }

    public boolean tryAcquire(long timestamp, long tokens) {
        while (true) {
            State current = state.get();
            State refilled = refilled(current, timestamp);
            boolean granted = refilled.stored() >= tokens;
            State next = granted ? new State(refilled.stored() - tokens, refilled.lastRefill()) : refilled;
            if (next == current || state.compareAndSet(current, next)) {
                return granted;
            }
        }
    }

    public long available(long timestamp) {
        while (true) {
            State current = state.get();
            State refilled = refilled(current, timestamp);
            if (refilled == current || state.compareAndSet(current, refilled)) {
                return refilled.stored();
            }
        }
    }

    private State refilled(State current, long timestamp) {
        if (timestamp <= current.lastRefill()) {
            return current;
        }
        long elapsed = timestamp - current.lastRefill();
        long stored = Math.min(capacity, current.stored() + elapsed * refillPerSecond);
        return new State(stored, timestamp);
    }
}
