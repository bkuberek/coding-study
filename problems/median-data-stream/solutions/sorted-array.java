import java.util.*;

public class MedianFinder {
    private final List<Integer> values = new ArrayList<>(); // every number so far, ascending

    public MedianFinder() {
    }

    public void addNum(int num) {
        // binarySearch returns -(insertion point) - 1 when num is absent.
        int index = Collections.binarySearch(values, num);
        values.add(index >= 0 ? index : -index - 1, num);
    }

    public double findMedian() {
        int middle = values.size() / 2;
        if (values.size() % 2 == 1) {
            return values.get(middle);
        }
        return (values.get(middle - 1) + values.get(middle)) / 2.0;
    }
}
