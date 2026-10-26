import java.util.HashMap;

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

    public LRUCache(int capacity) {
        this.capacity = capacity;
        head.next = tail;
        tail.prev = head;
    }

    public int get(int key) {
        Node node = nodes.get(key);
        if (node == null) {
            return -1;
        }
        unlink(node);
        append(node);
        return node.value;
    }

    public synchronized void put(int key, int value) {
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
    }

    public synchronized int size() {
        return nodes.size();
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
