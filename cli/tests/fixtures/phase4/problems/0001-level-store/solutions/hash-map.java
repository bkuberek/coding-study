import java.util.*;

public class LevelStore {
    private final Map<String, String> values = new HashMap<>();

    public LevelStore() {
    }

    public void put(String key, String value) {
        values.put(key, value);
    }

    public String get(String key) {
        return values.getOrDefault(key, "");
    }

    public boolean remove(String key) {
        return values.remove(key) != null;
    }

    public int size() {
        return values.size();
    }

    public String[] keysWithPrefix(String prefix) {
        return values.keySet().stream()
                .filter(key -> key.startsWith(prefix))
                .sorted()
                .toArray(String[]::new);
    }
}
