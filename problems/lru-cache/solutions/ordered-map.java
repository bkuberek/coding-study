import java.util.*;

public class LRUCache {
    private final Map<Integer, Integer> entries;

    public LRUCache(int capacity) {
        // accessOrder = true: every get or put moves the key to the end of the iteration order.
        entries = new LinkedHashMap<>(16, 0.75f, true) {
            @Override
            protected boolean removeEldestEntry(Map.Entry<Integer, Integer> eldest) {
                return size() > capacity;
            }
        };
    }

    public int get(int key) {
        return entries.getOrDefault(key, -1);
    }

    public void put(int key, int value) {
        entries.put(key, value);
    }
}
