import java.util.*;

public class Solution {
    public int[] maxSlidingWindow(int[] nums, int k) {
        PriorityQueue<Integer> heap = new PriorityQueue<>((a, b) -> Integer.compare(nums[b], nums[a]));
        int[] maxima = new int[nums.length - k + 1];
        for (int right = 0; right < nums.length; right++) {
            heap.add(right);
            if (right >= k - 1) {
                while (heap.peek() <= right - k) {
                    heap.poll();
                }
                maxima[right - k + 1] = nums[heap.peek()];
            }
        }
        return maxima;
    }
}
