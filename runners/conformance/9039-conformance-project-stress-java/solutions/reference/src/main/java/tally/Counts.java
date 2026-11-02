package tally;

import java.util.HashMap;
import java.util.Map;

/** Counts by key; every read and write holds the monitor. */
final class Counts {
    private final Map<String, Integer> counts = new HashMap<>();

    synchronized int add(String key, int amount) {
        int count = counts.getOrDefault(key, 0) + amount;
        counts.put(key, count);
        return count;
    }

    synchronized int of(String key) {
        return counts.getOrDefault(key, 0);
    }

    synchronized boolean take(String key, int amount) {
        int count = counts.getOrDefault(key, 0);
        if (count < amount) {
            return false;
        }
        counts.put(key, count - amount);
        return true;
    }
}
