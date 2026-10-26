public class StressCounter {
    private int count;

    public int increment() throws InterruptedException {
        int current = count;
        count = current + 1;
        return current + 1;
    }
}
