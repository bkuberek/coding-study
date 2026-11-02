package tally;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/** Counts by key; `add` reads a count, yields, then writes it, without the monitor. */
final class Counts {
    private final Map<String, Integer> counts = new ConcurrentHashMap<>();

    int add(String key, int amount) {
        int count = counts.getOrDefault(key, 0) + amount;
        Thread.yield();
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
