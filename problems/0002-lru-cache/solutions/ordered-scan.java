import java.util.*;

public class LRUCache {
    private record Entry(int key, int value) {}

    private final int capacity;
    // Ordered from least to most recently used.
    private final List<Entry> entries = new ArrayList<>();

    public LRUCache(int capacity) {
        this.capacity = capacity;
    }

    public int get(int key) {
        int index = indexOf(key);
        if (index < 0) {
            return -1;
        }
        Entry entry = entries.remove(index);
        entries.add(entry);
        return entry.value();
    }

    public void put(int key, int value) {
        int index = indexOf(key);
        if (index >= 0) {
            entries.remove(index);
        } else if (entries.size() == capacity) {
            entries.remove(0);
        }
        entries.add(new Entry(key, value));
    }

    private int indexOf(int key) {
        for (int i = 0; i < entries.size(); i++) {
            if (entries.get(i).key() == key) {
                return i;
            }
        }
        return -1;
    }
}
