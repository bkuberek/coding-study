import java.util.*;

public class Solution {
    public int lengthOfLIS(int[] nums) {
        // memo[start] is the longest increasing subsequence that begins at nums[start], or 0.
        int[] memo = new int[nums.length];
        int answer = 0;
        for (int start = 0; start < nums.length; start++) {
            answer = Math.max(answer, longestFrom(start, nums, memo));
        }
        return answer;
    }

    private int longestFrom(int start, int[] nums, int[] memo) {
        if (memo[start] == 0) {
            int best = 1;
            for (int following = start + 1; following < nums.length; following++) {
                if (nums[following] > nums[start]) {
                    best = Math.max(best, 1 + longestFrom(following, nums, memo));
                }
            }
            memo[start] = best;
        }
        return memo[start];
    }
}
