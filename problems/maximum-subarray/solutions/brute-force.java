import java.util.*;

public class Solution {
    public int maxSubArray(int[] nums) {
        int best = nums[0];
        for (int start = 0; start < nums.length; start++) {
            int total = 0;
            for (int end = start; end < nums.length; end++) {
                total += nums[end];
                best = Math.max(best, total);
            }
        }
        return best;
    }
}
