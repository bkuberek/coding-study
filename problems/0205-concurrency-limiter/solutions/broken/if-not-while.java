public class ConcurrencyLimiter {
    private int permits;

    public ConcurrencyLimiter(int limit) {
        this.permits = limit;
    }

    public synchronized void acquire() throws InterruptedException {
        if (permits == 0) {
            wait();
        }
        permits--;
    }

    public synchronized boolean tryAcquire() {
        if (permits == 0) {
            return false;
        }
        permits--;
        return true;
    }

    public synchronized void release() {
        permits++;
        notifyAll();
    }

    public synchronized int available() {
        return permits;
    }
}
