import java.util.ArrayDeque;
import java.util.concurrent.Semaphore;

public class BoundedBlockingQueue {
    private final ArrayDeque<Integer> items = new ArrayDeque<>();
    private final Object mutex = new Object();
    private final Semaphore freeSlots;
    private final Semaphore stored = new Semaphore(0);

    public BoundedBlockingQueue(int capacity) {
        this.freeSlots = new Semaphore(capacity);
    }

    public void put(int value) throws InterruptedException {
        freeSlots.acquire();
        synchronized (mutex) {
            items.addLast(value);
        }
        stored.release();
    }

    public int take() throws InterruptedException {
        stored.acquire();
        int value;
        synchronized (mutex) {
            value = items.removeFirst();
        }
        freeSlots.release();
        return value;
    }

    public int size() {
        synchronized (mutex) {
            return items.size();
        }
    }
}
