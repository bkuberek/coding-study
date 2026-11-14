import java.util.*;

public class Solution {
    public boolean canPartition(int[] nums) {
        int total = Arrays.stream(nums).sum();
        if (total % 2 == 1) {
            return false;
        }
        int target = total / 2;
        // reach[i][s] is true when some of the first i elements add up to exactly s.
        boolean[][] reach = new boolean[nums.length + 1][target + 1];
        reach[0][0] = true;
        for (int i = 1; i <= nums.length; i++) {
            int value = nums[i - 1];
            for (int s = 0; s <= target; s++) {
                reach[i][s] = reach[i - 1][s] || (s >= value && reach[i - 1][s - value]);
            }
        }
        return reach[nums.length][target];
    }
}
