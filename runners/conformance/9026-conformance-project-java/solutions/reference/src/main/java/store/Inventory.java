package store;

import store.labels.Labels;

/**
 * The entry class: `cstudy` loads `store.Inventory`. It uses a class of its own package that the
 * reference adds and one of a subpackage that the starter holds.
 */
public class Inventory {
    private final Counts counts = new Counts();

    public int add(String name, int count) {
        return counts.add(name, count);
    }

    public String label(String name) {
        return Labels.labelFor(name, counts.of(name));
    }
}
