import java.util.*;

public class Solution {
    public int findTargetSumWays(int[] nums, int target) {
        int total = Arrays.stream(nums).sum();
        // With P the plus part: P - (total - P) = target, so P = (total + target) / 2.
        if (Math.abs(target) > total || (total + target) % 2 != 0) {
            return 0;
        }
        int plus = (total + target) / 2;
        // ways[p] counts the subsets of the values seen so far that add up to p.
        int[] ways = new int[plus + 1];
        ways[0] = 1;
        for (int value : nums) {
            // Decreasing p: ways[p - value] still excludes this value, so it is used at most once.
            for (int p = plus; p >= value; p--) {
                ways[p] += ways[p - value];
            }
        }
        return ways[plus];
    }
}
