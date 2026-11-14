import java.util.*;

public class TimeMap {
    private record Entry(int timestamp, String value) {}

    private final Map<String, List<Entry>> history = new HashMap<>();

    public TimeMap() {
    }

    public void set(String key, String value, int timestamp) {
        history.computeIfAbsent(key, k -> new ArrayList<>()).add(new Entry(timestamp, value));
    }

    public String get(String key, int timestamp) {
        List<Entry> entries = history.getOrDefault(key, List.of());
        for (int i = entries.size() - 1; i >= 0; i--) {
            if (entries.get(i).timestamp() <= timestamp) {
                return entries.get(i).value();
            }
        }
        return "";
    }
}
