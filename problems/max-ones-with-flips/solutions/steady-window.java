public class Solution {
    public int longestOnes(int[] nums, int k) {
        int left = 0;
        int flipsLeft = k;
        for (int value : nums) {
            if (value == 0) {
                flipsLeft--;
            }
            if (flipsLeft < 0 && nums[left++] == 0) {
                flipsLeft++;
            }
        }
        return nums.length - left;
    }
}
