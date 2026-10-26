import java.util.concurrent.Semaphore;

public class ReadWriteLock {
    private final Semaphore writers = new Semaphore(1);
    private volatile boolean writing;
    private volatile int readers;

    public void acquireRead() throws InterruptedException {
        while (writing) {
            Thread.sleep(0);
        }
        readers++;
    }

    public void releaseRead() {
        readers--;
    }

    public void acquireWrite() throws InterruptedException {
        writers.acquire();
        while (readers > 0) {
            Thread.sleep(0);
        }
        writing = true;
    }

    public void releaseWrite() {
        writing = false;
        writers.release();
    }

    public boolean tryAcquireRead() {
        if (writing) {
            return false;
        }
        readers++;
        return true;
    }

    public boolean tryAcquireWrite() {
        if (!writers.tryAcquire()) {
            return false;
        }
        if (readers > 0) {
            writers.release();
            return false;
        }
        writing = true;
        return true;
    }
}
