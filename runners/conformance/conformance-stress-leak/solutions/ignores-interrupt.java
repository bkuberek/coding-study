public class StressLeak {
    public void spin() {
        while (true) {
            Thread.onSpinWait();
        }
    }

    public void fail() {
        throw new IllegalStateException("leak");
    }

    public void noop() {
    }
}
