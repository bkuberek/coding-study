import java.util.*;

public class TimeMap {
    private static final class History {
        private int[] timestamps = new int[4];
        private final List<String> values = new ArrayList<>();

        void add(int timestamp, String value) {
            if (values.size() == timestamps.length) {
                timestamps = Arrays.copyOf(timestamps, timestamps.length * 2);
            }
            timestamps[values.size()] = timestamp;
            values.add(value);
        }

        String valueAt(int timestamp) {
            // Find how many writes happened at or before timestamp (upper bound).
            int low = 0;
            int high = values.size();
            while (low < high) {
                int middle = (low + high) >>> 1;
                if (timestamps[middle] <= timestamp) {
                    low = middle + 1;
                } else {
                    high = middle;
                }
            }
            return low > 0 ? values.get(low - 1) : "";
        }
    }

    private final Map<String, History> history = new HashMap<>();

    public TimeMap() {
    }

    public void set(String key, String value, int timestamp) {
        history.computeIfAbsent(key, k -> new History()).add(timestamp, value);
    }

    public String get(String key, int timestamp) {
        History entries = history.get(key);
        return entries == null ? "" : entries.valueAt(timestamp);
    }
}
