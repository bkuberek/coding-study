public class ReadWriteLock {
    private int readers;
    private boolean writing;
    private int waitingWriters;

    public synchronized void acquireRead() throws InterruptedException {
        while (writing || waitingWriters > 0) {
            wait();
        }
        readers++;
    }

    public synchronized void releaseRead() {
        readers--;
        if (readers == 0) {
            notifyAll();
        }
    }

    public synchronized void acquireWrite() throws InterruptedException {
        waitingWriters++;
        if (writing || readers > 0) {
            wait();
        }
        waitingWriters--;
        writing = true;
    }

    public synchronized void releaseWrite() {
        writing = false;
        notifyAll();
    }

    public synchronized boolean tryAcquireRead() {
        if (writing || waitingWriters > 0) {
            return false;
        }
        readers++;
        return true;
    }

    public synchronized boolean tryAcquireWrite() {
        if (writing || readers > 0) {
            return false;
        }
        writing = true;
        return true;
    }
}
