import java.util.HashMap;
import java.util.concurrent.locks.ReentrantLock;

public class LRUCache {
    private static final class Node {
        final int key;
        int value;
        Node prev;
        Node next;

        Node(int key, int value) {
            this.key = key;
            this.value = value;
        }
    }

    private final int capacity;
    private final HashMap<Integer, Node> nodes = new HashMap<>();
    private final Node head = new Node(-1, -1);
    private final Node tail = new Node(-1, -1);
    private final ReentrantLock lock = new ReentrantLock();

    public LRUCache(int capacity) {
        this.capacity = capacity;
        head.next = tail;
        tail.prev = head;
    }

    public int get(int key) {
        lock.lock();
        try {
            Node node = nodes.get(key);
            if (node == null) {
                return -1;
            }
            unlink(node);
            append(node);
            return node.value;
        } finally {
            lock.unlock();
        }
    }

    public void put(int key, int value) {
        lock.lock();
        try {
            Node node = nodes.get(key);
            if (node != null) {
                node.value = value;
                unlink(node);
                append(node);
                return;
            }
            if (nodes.size() == capacity) {
                Node eldest = head.next;
                unlink(eldest);
                nodes.remove(eldest.key);
            }
            node = new Node(key, value);
            nodes.put(key, node);
            append(node);
        } finally {
            lock.unlock();
        }
    }

    public int size() {
        lock.lock();
        try {
            return nodes.size();
        } finally {
            lock.unlock();
        }
    }

    private void unlink(Node node) {
        node.prev.next = node.next;
        node.next.prev = node.prev;
    }

    private void append(Node node) {
        Node last = tail.prev;
        last.next = node;
        node.prev = last;
        node.next = tail;
        tail.prev = node;
    }
}
