package store;

import java.util.HashMap;
import java.util.Map;

/** Stock counts by name. */
final class Counts {
    private final Map<String, Integer> counts = new HashMap<>();

    int add(String name, int count) {
        return counts.merge(name, count, Integer::sum);
    }

    int of(String name) {
        return counts.getOrDefault(name, 0);
    }
}
