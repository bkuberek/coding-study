package store.labels;

/** Labels for stock counts, in a package of their own. */
public final class Labels {
    public static final String SEPARATOR = ": ";

    private Labels() {
    }

    public static String labelFor(String name, int count) {
        return name + SEPARATOR + count;
    }
}
