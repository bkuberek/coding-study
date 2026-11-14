import java.util.*;

public class TransactionalStore {
    /** The current view, open transactions included. */
    private final Map<String, String> data = new HashMap<>();
    private final Map<String, Integer> counts = new HashMap<>();
    /** One undo log per open transaction, innermost first: key to value before its first change (null: absent). */
    private final Deque<Map<String, String>> undo = new ArrayDeque<>();
    /** Permanent values per key, by the sequence number from which they hold (null value: removed). */
    private final Map<String, TreeMap<Integer, Optional<String>>> history = new HashMap<>();
    private int sequence;
    private final List<Integer> snapshots = new ArrayList<>();

    public TransactionalStore() {
    }

    // Level 1
    public void set(long timestamp, String key, String value) {
        change(key, value);
    }

    public String get(long timestamp, String key) {
        return data.getOrDefault(key, "");
    }

    public boolean remove(long timestamp, String key) {
        if (!data.containsKey(key)) {
            return false;
        }
        change(key, null);
        return true;
    }

    public int count(long timestamp, String value) {
        return counts.getOrDefault(value, 0);
    }

    // Level 2
    public void begin(long timestamp) {
        undo.push(new HashMap<>());
    }

    public boolean rollback(long timestamp) {
        if (undo.isEmpty()) {
            return false;
        }
        undo.pop().forEach(this::assign);
        return true;
    }

    // Level 3
    public int depth(long timestamp) {
        return undo.size();
    }

    // Level 4
    public int commit(long timestamp) {
        if (undo.isEmpty()) {
            return -1;
        }
        Map<String, String> changed = undo.pop();
        if (!undo.isEmpty()) {
            Map<String, String> enclosing = undo.peek();
            changed.forEach((key, previous) -> {
                if (!enclosing.containsKey(key)) {
                    enclosing.put(key, previous);
                }
            });
            return 0;
        }
        makePermanent(changed.keySet());
        snapshots.add(sequence);
        return snapshots.size();
    }

    public String getSnapshot(long timestamp, int version, String key) {
        TreeMap<Integer, Optional<String>> values = history.get(key);
        if (version < 1 || version > snapshots.size() || values == null) {
            return "";
        }
        Map.Entry<Integer, Optional<String>> entry = values.floorEntry(snapshots.get(version - 1));
        return entry == null ? "" : entry.getValue().orElse("");
    }

    private void change(String key, String value) {
        Map<String, String> innermost = undo.peek();
        if (innermost == null) {
            assign(key, value);
            makePermanent(List.of(key));
            return;
        }
        if (!innermost.containsKey(key)) {
            innermost.put(key, data.get(key));
        }
        assign(key, value);
    }

    private void assign(String key, String value) {
        String previous = value == null ? data.remove(key) : data.put(key, value);
        if (previous != null) {
            counts.merge(previous, -1, Integer::sum);
        }
        if (value != null) {
            counts.merge(value, 1, Integer::sum);
        }
    }

    private void makePermanent(Collection<String> keys) {
        sequence++;
        for (String key : keys) {
            history.computeIfAbsent(key, k -> new TreeMap<>()).put(sequence, Optional.ofNullable(data.get(key)));
        }
    }
}
