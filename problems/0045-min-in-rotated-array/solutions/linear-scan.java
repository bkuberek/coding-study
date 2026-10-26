public class Solution {
    public int findMin(int[] nums) {
        int smallest = nums[0];
        for (int value : nums) {
            if (value < smallest) {
                smallest = value;
            }
        }
        return smallest;
    }
}
