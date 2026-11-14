import java.util.*;

public class Solution {
    public int[] topKFrequent(int[] nums, int k) {
        Map<Integer, Integer> counts = new HashMap<>();
        for (int value : nums) {
            counts.merge(value, 1, Integer::sum);
        }
        // PriorityQueue is a min-heap: its head is the weakest of the k values kept so far.
        PriorityQueue<Integer> heap = new PriorityQueue<>(Comparator.comparingInt(counts::get));
        for (int value : counts.keySet()) {
            if (heap.size() < k) {
                heap.offer(value);
            } else if (counts.get(value) > counts.get(heap.peek())) {
                heap.poll();
                heap.offer(value);
            }
        }
        return heap.stream().mapToInt(Integer::intValue).toArray();
    }
}
