public class Solution {
    public int search(int[] nums, int target) {
        // Invariant: if target is in nums, its index lies in [low, high].
        int low = 0;
        int high = nums.length - 1;
        while (low <= high) {
            int middle = low + (high - low) / 2;
            if (nums[middle] == target) {
                return middle;
            }
            if (nums[middle] < target) {
                low = middle + 1;
            } else {
                high = middle - 1;
            }
        }
        return -1;
    }
}
