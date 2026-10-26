import java.util.*;

public class Solution {
    public int findTargetSumWays(int[] nums, int target) {
        return count(nums, target, 0, 0);
    }

    private static int count(int[] nums, int target, int index, int total) {
        if (index == nums.length) {
            return total == target ? 1 : 0;
        }
        // Give nums[index] a plus sign, then a minus sign.
        return count(nums, target, index + 1, total + nums[index])
                + count(nums, target, index + 1, total - nums[index]);
    }
}
