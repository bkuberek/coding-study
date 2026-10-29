public class Solution {
    public int searchInsert(int[] nums, int target) {
        int low = 0;
        int high = nums.length; // the answer lies in [low, high]
        while (low < high) {
            int middle = low + (high - low) / 2;
            if (nums[middle] < target) {
                low = middle + 1;
            } else {
                high = middle;
            }
        }
        return low;
    }
}
