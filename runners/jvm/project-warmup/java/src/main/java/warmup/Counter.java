package warmup;

/**
 * The warm-up project's code: `cstudy doctor --fix` builds this folder online once, so every
 * library a Java project problem builds with is cached for its offline builds.
 */
public class Counter {
    private int count;

    public int add(int amount) {
        count += amount;
        return count;
    }
}
