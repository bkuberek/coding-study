import java.util.*;

public class Solution {
    private int[] nums;
    private int target;
    private int total;
    // ways[index][running + total] caches the count from that state; -1 is unknown.
    private int[][] ways;

    public int findTargetSumWays(int[] nums, int target) {
        this.nums = nums;
        this.target = target;
        total = Arrays.stream(nums).sum();
        ways = new int[nums.length][2 * total + 1];
        for (int[] row : ways) {
            Arrays.fill(row, -1);
        }
        return count(0, 0);
    }

    private int count(int index, int running) {
        if (index == nums.length) {
            return running == target ? 1 : 0;
        }
        int offset = running + total;
        if (ways[index][offset] < 0) {
            ways[index][offset] = count(index + 1, running + nums[index]) + count(index + 1, running - nums[index]);
        }
        return ways[index][offset];
    }
}
