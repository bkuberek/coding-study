import java.util.*;

public class Counter {
    private int count;

    public Counter() {
    }

    public int increment() {
        count++;
        return count;
    }

    public int fail() {
        throw new IllegalStateException("counter failure");
    }
}
