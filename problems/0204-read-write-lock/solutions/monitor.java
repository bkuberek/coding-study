import java.util.concurrent.locks.Condition;
import java.util.concurrent.locks.ReentrantLock;

public class ReadWriteLock {
    private final ReentrantLock lock = new ReentrantLock();
    private final Condition readable = lock.newCondition();
    private final Condition writable = lock.newCondition();
    private int readers;
    private boolean writing;
    private int waitingWriters;

    public void acquireRead() throws InterruptedException {
        lock.lock();
        try {
            while (writing || waitingWriters > 0) {
                readable.await();
            }
            readers++;
        } finally {
            lock.unlock();
        }
    }

    public void releaseRead() {
        lock.lock();
        try {
            readers--;
            if (readers == 0) {
                writable.signal();
            }
        } finally {
            lock.unlock();
        }
    }

    public void acquireWrite() throws InterruptedException {
        lock.lock();
        try {
            waitingWriters++;
            try {
                while (writing || readers > 0) {
                    writable.await();
                }
            } catch (InterruptedException e) {
                waitingWriters--;
                if (waitingWriters == 0 && !writing) {
                    readable.signalAll();
                }
                throw e;
            }
            waitingWriters--;
            writing = true;
        } finally {
            lock.unlock();
        }
    }

    public void releaseWrite() {
        lock.lock();
        try {
            writing = false;
            if (waitingWriters > 0) {
                writable.signal();
            } else {
                readable.signalAll();
            }
        } finally {
            lock.unlock();
        }
    }

    public boolean tryAcquireRead() {
        lock.lock();
        try {
            if (writing || waitingWriters > 0) {
                return false;
            }
            readers++;
            return true;
        } finally {
            lock.unlock();
        }
    }

    public boolean tryAcquireWrite() {
        lock.lock();
        try {
            if (writing || readers > 0) {
                return false;
            }
            writing = true;
            return true;
        } finally {
            lock.unlock();
        }
    }
}
