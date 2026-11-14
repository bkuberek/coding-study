import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;

public class ConcurrencyLimiter {
    private final Semaphore permits;

    public ConcurrencyLimiter(int limit) {
        this.permits = new Semaphore(limit, true);
    }

    public void acquire() throws InterruptedException {
        permits.acquire();
    }

    public boolean tryAcquire() {
        try {
            return permits.tryAcquire(0, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return false;
        }
    }

    public void release() {
        permits.release();
    }

    public int available() {
        return permits.availablePermits();
    }
}
