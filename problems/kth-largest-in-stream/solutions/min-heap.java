import java.util.*;

public class KthLargestTracker {
    private final int k;
    // The k largest numbers seen so far. PriorityQueue keeps the least element at its head.
    private final PriorityQueue<Integer> top = new PriorityQueue<>();

    public KthLargestTracker(int k, int[] nums) {
        this.k = k;
        for (int value : nums) {
            offer(value);
        }
    }

    public int add(int value) {
        offer(value);
        return top.peek();
    }

    private void offer(int value) {
        top.offer(value);
        if (top.size() > k) {
            // k + 1 numbers are in the heap; the smallest cannot be among the k largest.
            top.poll();
        }
    }
}
