import java.util.concurrent.atomic.AtomicInteger;

public class StressCounter {
    private final AtomicInteger count = new AtomicInteger();

    public int increment() throws InterruptedException {
        return count.incrementAndGet();
    }
}
