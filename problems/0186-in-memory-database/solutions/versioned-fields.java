import java.util.*;

public class InMemoryDatabase {
    /** One write to a field: a value (null for a deletion), from {@code since} until {@code expiresAt}. */
    private record Version(long since, String value, Long expiresAt) {
        boolean visibleAt(long moment) {
            return value != null && (expiresAt == null || moment < expiresAt);
        }
    }

    /** Every version of one field; timestamps arrive in increasing order, so a TreeMap by time is exact. */
    private static final class FieldHistory {
        private final TreeMap<Long, Version> versions = new TreeMap<>();

        void record(Version version) {
            versions.put(version.since(), version);
        }

        String valueAt(long moment) {
            Map.Entry<Long, Version> entry = versions.floorEntry(moment);
            if (entry == null || !entry.getValue().visibleAt(moment)) {
                return null;
            }
            return entry.getValue().value();
        }
    }

    private final Map<String, Map<String, FieldHistory>> records = new HashMap<>();

    public InMemoryDatabase() {
    }

    // Level 1
    public void set(long timestamp, String key, String field, String value) {
        write(key, field, new Version(timestamp, value, null));
    }

    public String get(long timestamp, String key, String field) {
        String value = valueAt(key, field, timestamp);
        return value == null ? "" : value;
    }

    public boolean remove(long timestamp, String key, String field) {
        if (valueAt(key, field, timestamp) == null) {
            return false;
        }
        write(key, field, new Version(timestamp, null, null));
        return true;
    }

    // Level 2
    public List<String> scan(long timestamp, String key) {
        return scanFields(key, "", timestamp);
    }

    public List<String> scanByPrefix(long timestamp, String key, String prefix) {
        return scanFields(key, prefix, timestamp);
    }

    // Level 3
    public void setWithTtl(long timestamp, String key, String field, String value, long ttl) {
        write(key, field, new Version(timestamp, value, timestamp + ttl));
    }

    // Level 4
    public String getAt(long timestamp, String key, String field, long atTimestamp) {
        String value = valueAt(key, field, atTimestamp);
        return value == null ? "" : value;
    }

    public List<String> scanAt(long timestamp, String key, long atTimestamp) {
        return scanFields(key, "", atTimestamp);
    }

    private void write(String key, String field, Version version) {
        records.computeIfAbsent(key, k -> new HashMap<>())
                .computeIfAbsent(field, f -> new FieldHistory())
                .record(version);
    }

    private String valueAt(String key, String field, long moment) {
        FieldHistory history = records.getOrDefault(key, Map.of()).get(field);
        return history == null ? null : history.valueAt(moment);
    }

    private List<String> scanFields(String key, String prefix, long moment) {
        TreeMap<String, String> visible = new TreeMap<>();
        for (Map.Entry<String, FieldHistory> entry : records.getOrDefault(key, Map.of()).entrySet()) {
            String value = entry.getValue().valueAt(moment);
            if (entry.getKey().startsWith(prefix) && value != null) {
                visible.put(entry.getKey(), value);
            }
        }
        List<String> result = new ArrayList<>();
        visible.forEach((field, value) -> result.add(field + "(" + value + ")"));
        return result;
    }
}
