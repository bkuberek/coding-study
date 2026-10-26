import java.util.*;
import java.util.function.Supplier;

public class CacheService {
    /** Tracks the live keys and names the one to evict when the cache is full. */
    private interface EvictionPolicy {
        void admit(String key);

        void touch(String key);

        void forget(String key);

        String victim();
    }

    private static class LruPolicy implements EvictionPolicy {
        protected final LinkedHashSet<String> order = new LinkedHashSet<>(); // least recently used first

        public void admit(String key) {
            order.add(key);
        }

        public void touch(String key) {
            order.remove(key);
            order.add(key);
        }

        public void forget(String key) {
            order.remove(key);
        }

        public String victim() {
            return order.iterator().next();
        }
    }

    private static final class FifoPolicy extends LruPolicy {
        /** Using a key does not change its place: the oldest insertion goes first. */
        @Override
        public void touch(String key) {
        }
    }

    /** Least frequently used first; among equal counts, least recently used first. */
    private static final class LfuPolicy implements EvictionPolicy {
        private final Map<String, Integer> counts = new HashMap<>();
        private final Map<Integer, LinkedHashSet<String>> buckets = new HashMap<>();
        private int lowest = 1; // never above the lowest count in use

        public void admit(String key) {
            place(key, 1);
            lowest = 1;
        }

        public void touch(String key) {
            int count = counts.get(key);
            buckets.get(count).remove(key);
            place(key, count + 1);
        }

        public void forget(String key) {
            buckets.get(counts.remove(key)).remove(key);
        }

        public String victim() {
            while (buckets.getOrDefault(lowest, new LinkedHashSet<>()).isEmpty()) {
                lowest++;
            }
            return buckets.get(lowest).iterator().next();
        }

        private void place(String key, int count) {
            counts.put(key, count);
            buckets.computeIfAbsent(count, c -> new LinkedHashSet<>()).add(key);
        }
    }

    private static final Map<String, Supplier<EvictionPolicy>> POLICIES =
            Map.of("LRU", LruPolicy::new, "LFU", LfuPolicy::new, "FIFO", FifoPolicy::new);

    private static final class Entry {
        String value;
        Long expiresAt; // null: never expires

        Entry(String value, Long expiresAt) {
            this.value = value;
            this.expiresAt = expiresAt;
        }

        boolean expired(long now) {
            return expiresAt != null && now >= expiresAt;
        }
    }

    private record Expiry(long expiresAt, String key) {
    }

    private final int capacity;
    private final EvictionPolicy policy;
    private final Map<String, Entry> entries = new HashMap<>();
    /** Min-heap by expiry time; pairs that no longer match their entry are skipped. */
    private final PriorityQueue<Expiry> expiries = new PriorityQueue<>(Comparator.comparingLong(Expiry::expiresAt));
    private int hits;
    private int misses;
    private int evictions;
    private int expirations;

    public CacheService(int capacity, String policy) {
        this.capacity = capacity;
        this.policy = POLICIES.getOrDefault(policy, LruPolicy::new).get();
    }

    public void put(long timestamp, String key, String value, long ttl) {
        Long expiresAt = ttl > 0 ? timestamp + ttl : null;
        Entry entry = live(timestamp, key);
        if (entry != null) {
            entry.value = value;
            entry.expiresAt = expiresAt;
            policy.touch(key);
        } else {
            makeRoom(timestamp);
            entries.put(key, new Entry(value, expiresAt));
            policy.admit(key);
        }
        if (expiresAt != null) {
            expiries.add(new Expiry(expiresAt, key));
        }
    }

    public String get(long timestamp, String key) {
        Entry entry = live(timestamp, key);
        if (entry == null) {
            misses++;
            return "";
        }
        hits++;
        policy.touch(key);
        return entry.value;
    }

    public boolean remove(long timestamp, String key) {
        if (live(timestamp, key) == null) {
            return false;
        }
        drop(key);
        return true;
    }

    public int size(long timestamp) {
        purgeExpired(timestamp);
        return entries.size();
    }

    public int[] stats() {
        return new int[] {hits, misses, evictions, expirations};
    }

    private Entry live(long now, String key) {
        Entry entry = entries.get(key);
        if (entry != null && entry.expired(now)) {
            expire(key);
            return null;
        }
        return entry;
    }

    private void makeRoom(long now) {
        if (entries.size() < capacity) {
            return;
        }
        purgeExpired(now);
        if (entries.size() >= capacity) {
            drop(policy.victim());
            evictions++;
        }
    }

    private void purgeExpired(long now) {
        while (!expiries.isEmpty() && expiries.peek().expiresAt() <= now) {
            Expiry expiry = expiries.poll();
            Entry entry = entries.get(expiry.key());
            if (entry != null && entry.expiresAt != null && entry.expiresAt == expiry.expiresAt()) {
                expire(expiry.key());
            }
        }
    }

    private void expire(String key) {
        drop(key);
        expirations++;
    }

    private void drop(String key) {
        entries.remove(key);
        policy.forget(key);
    }
}
