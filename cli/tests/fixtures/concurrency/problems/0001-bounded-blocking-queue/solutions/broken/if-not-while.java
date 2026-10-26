import java.util.ArrayDeque;

public class BoundedBlockingQueue {
    private final int capacity;
    private final ArrayDeque<Integer> items = new ArrayDeque<>();

    public BoundedBlockingQueue(int capacity) {
        this.capacity = capacity;
    }

    public synchronized void put(int value) throws InterruptedException {
        if (items.size() >= capacity) {
            wait();
        }
        items.addLast(value);
        notifyAll();
    }

    public synchronized int take() throws InterruptedException {
        if (items.isEmpty()) {
            wait();
        }
        int value = items.removeFirst();
        notifyAll();
        return value;
    }

    public synchronized int size() {
        return items.size();
    }
}
