import java.util.concurrent.CountDownLatch;

public class StressGate {
    private final CountDownLatch open = new CountDownLatch(1);

    public void enter() throws InterruptedException {
        open.await();
    }
}
