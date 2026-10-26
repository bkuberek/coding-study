// Debug: Window Shrink. Some tests fail: find the bug and fix it.
import java.util.*;

public class Solution {
    public int maxDistinctWindowSum(int[] nums, int k) {
        Map<Integer, Integer> counts = new HashMap<>();
        int windowSum = 0;
        int best = 0;
        for (int right = 0; right < nums.length; right++) {
            counts.merge(nums[right], 1, Integer::sum);
            windowSum += nums[right];
            if (right >= k) {
                int outgoing = nums[right - k];
                counts.put(outgoing, counts.get(outgoing) - 1);
                windowSum -= outgoing;
            }
            if (right >= k - 1 && counts.size() == k) {
                best = Math.max(best, windowSum);
            }
        }
        return best;
    }
}
