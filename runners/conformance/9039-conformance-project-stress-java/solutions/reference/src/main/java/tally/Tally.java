package tally;

/** The entry class, which worker threads share from level 2. */
public class Tally {
    private final Counts counts = new Counts();

    public int add(String key, int amount) {
        return counts.add(key, amount);
    }

    public int count(String key) {
        return counts.of(key);
    }

    public boolean take(String key, int amount) {
        return counts.take(key, amount);
    }
}
