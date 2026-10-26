import java.util.*;

public class MedianFinder {
    // low: the smaller half, largest on top. high: the larger half, smallest on top.
    // low holds as many values as high, or one more.
    private final PriorityQueue<Integer> low = new PriorityQueue<>(Comparator.reverseOrder());
    private final PriorityQueue<Integer> high = new PriorityQueue<>();

    public MedianFinder() {
    }

    public void addNum(int num) {
        // Route the number through low so that every value in low stays <= every value in high.
        low.offer(num);
        high.offer(low.poll());
        if (high.size() > low.size()) {
            low.offer(high.poll());
        }
    }

    public double findMedian() {
        if (low.size() > high.size()) {
            return low.peek();
        }
        return (low.peek() + high.peek()) / 2.0;
    }
}
