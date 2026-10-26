// Running Maximum (debugging): some tests fail. Find the bug and fix it.
public class Solution {
    public int[] runningMax(int[] nums) {
        int[] result = new int[nums.length];
        int best = 0;
        for (int i = 0; i < nums.length; i++) {
            best = Math.max(best, nums[i]);
            result[i] = best;
        }
        return result;
    }
}
