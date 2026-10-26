import java.util.ArrayDeque;

public class BoundedBlockingQueue {
    private final int capacity;
    private final ArrayDeque<Integer> items = new ArrayDeque<>();

    public BoundedBlockingQueue(int capacity) {
        this.capacity = capacity;
    }

    public void put(int value) throws InterruptedException {
        while (items.size() >= capacity) {
            Thread.sleep(0);
        }
        items.addLast(value);
    }

    public int take() throws InterruptedException {
        while (items.isEmpty()) {
            Thread.sleep(0);
        }
        return items.pollFirst();
    }

    public int size() {
        return items.size();
    }
}
