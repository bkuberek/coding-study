import java.util.*;

public class Solution {
    public int findTargetSumWays(int[] nums, int target) {
        int total = Arrays.stream(nums).sum();
        if (Math.abs(target) > total) {
            return 0;
        }
        // ways[i][running + total] counts the sign assignments of nums[:i] with that running total.
        int[][] ways = new int[nums.length + 1][2 * total + 1];
        ways[0][total] = 1;
        for (int i = 0; i < nums.length; i++) {
            int value = nums[i];
            for (int offset = 0; offset <= 2 * total; offset++) {
                int count = ways[i][offset];
                if (count > 0) {
                    ways[i + 1][offset + value] += count;
                    ways[i + 1][offset - value] += count;
                }
            }
        }
        return ways[nums.length][target + total];
    }
}
