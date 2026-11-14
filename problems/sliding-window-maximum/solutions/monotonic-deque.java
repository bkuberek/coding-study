import java.util.*;

public class Solution {
    public int[] maxSlidingWindow(int[] nums, int k) {
        Deque<Integer> candidates = new ArrayDeque<>();
        int[] maxima = new int[nums.length - k + 1];
        for (int right = 0; right < nums.length; right++) {
            while (!candidates.isEmpty() && nums[candidates.peekLast()] <= nums[right]) {
                candidates.pollLast();
            }
            candidates.addLast(right);
            if (candidates.peekFirst() <= right - k) {
                candidates.pollFirst();
            }
            if (right >= k - 1) {
                maxima[right - k + 1] = nums[candidates.peekFirst()];
            }
        }
        return maxima;
    }
}
