import java.util.concurrent.locks.ReentrantLock;

public class StressMutex {
    private final ReentrantLock mutex = new ReentrantLock();

    public void lock() throws InterruptedException {
        mutex.lockInterruptibly();
    }

    public void unlock() {
        mutex.unlock();
    }
}
