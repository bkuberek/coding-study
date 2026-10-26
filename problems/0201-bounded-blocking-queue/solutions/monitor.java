import java.util.ArrayDeque;
import java.util.concurrent.locks.Condition;
import java.util.concurrent.locks.ReentrantLock;

public class BoundedBlockingQueue {
    private final int capacity;
    private final ArrayDeque<Integer> items = new ArrayDeque<>();
    private final ReentrantLock lock = new ReentrantLock();
    private final Condition notFull = lock.newCondition();
    private final Condition notEmpty = lock.newCondition();

    public BoundedBlockingQueue(int capacity) {
        this.capacity = capacity;
    }

    public void put(int value) throws InterruptedException {
        lock.lock();
        try {
            while (items.size() >= capacity) {
                notFull.await();
            }
            items.addLast(value);
            notEmpty.signal();
        } finally {
            lock.unlock();
        }
    }

    public int take() throws InterruptedException {
        lock.lock();
        try {
            while (items.isEmpty()) {
                notEmpty.await();
            }
            int value = items.removeFirst();
            notFull.signal();
            return value;
        } finally {
            lock.unlock();
        }
    }

    public int size() {
        lock.lock();
        try {
            return items.size();
        } finally {
            lock.unlock();
        }
    }
}
