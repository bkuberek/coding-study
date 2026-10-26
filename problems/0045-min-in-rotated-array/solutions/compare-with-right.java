public class Solution {
    public int findMin(int[] nums) {
        // Invariant: the index of the minimum lies in [low, high].
        int low = 0;
        int high = nums.length - 1;
        while (low < high) {
            int middle = (low + high) >>> 1;
            if (nums[middle] > nums[high]) {
                low = middle + 1;
            } else {
                high = middle;
            }
        }
        return nums[low];
    }
}
