public class Solution {
    public int missingNumber(int[] nums) {
        // Start with n, then fold in every index and value; present numbers cancel in pairs.
        int result = nums.length;
        for (int index = 0; index < nums.length; index++) {
            result ^= index ^ nums[index];
        }
        return result;
    }
}
