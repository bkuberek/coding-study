import java.util.*;

public class Solution {
    public int rob(int[] nums) {
        // memo[house] is the most cash obtainable from houses house..end, or -1 when unknown.
        int[] memo = new int[nums.length];
        Arrays.fill(memo, -1);
        return bestFrom(0, nums, memo);
    }

    private int bestFrom(int house, int[] nums, int[] memo) {
        if (house >= nums.length) {
            return 0;
        }
        if (memo[house] == -1) {
            int skip = bestFrom(house + 1, nums, memo);
            int take = nums[house] + bestFrom(house + 2, nums, memo);
            memo[house] = Math.max(skip, take);
        }
        return memo[house];
    }
}
