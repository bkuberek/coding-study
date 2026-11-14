import java.util.*;

public class Solution {
    public int findKthLargest(int[] nums, int k) {
        // The heap keeps the k largest values seen so far; its head is the smallest of them.
        PriorityQueue<Integer> heap = new PriorityQueue<>(k);
        for (int value : nums) {
            if (heap.size() < k) {
                heap.offer(value);
            } else if (value > heap.peek()) {
                heap.poll();
                heap.offer(value);
            }
        }
        return heap.peek();
    }
}
