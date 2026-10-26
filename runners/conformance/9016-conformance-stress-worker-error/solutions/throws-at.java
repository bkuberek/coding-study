public class StressFailer {
    public int step(int index) {
        if (index == 100) {
            throw new IllegalStateException("failed at 100");
        }
        return index;
    }
}
