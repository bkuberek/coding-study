public class Solution {
    public int search(int[] nums, int target) {
        // Find the first index whose value is >= target, in the half-open range [low, high).
        int low = 0;
        int high = nums.length;
        while (low < high) {
            int middle = (low + high) >>> 1;
            if (nums[middle] < target) {
                low = middle + 1;
            } else {
                high = middle;
            }
        }
        return low < nums.length && nums[low] == target ? low : -1;
    }
}
