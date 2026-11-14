import java.util.*;

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
    private final Map<Integer, Node> nodes = new HashMap<>();
    // Sentinels: head.next is the least recently used node, tail.prev the most recent.
    private final Node head = new Node(0, 0);
    private final Node tail = new Node(0, 0);

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

    public void put(int key, int value) {
        Node node = nodes.get(key);
        if (node != null) {
            node.value = value;
            unlink(node);
        } else {
            if (nodes.size() == capacity) {
                Node oldest = head.next;
                unlink(oldest);
                nodes.remove(oldest.key);
            }
            node = new Node(key, value);
            nodes.put(key, node);
        }
        append(node);
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
