public class Solution {
    public int searchInsert(int[] nums, int target) {
        // In a sorted array, target belongs right after every smaller value.
        int smaller = 0;
        for (int value : nums) {
            if (value < target) {
                smaller++;
            }
        }
        return smaller;
    }
}
