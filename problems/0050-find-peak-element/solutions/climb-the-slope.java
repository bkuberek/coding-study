public class Solution {
    public int findPeakElement(int[] nums) {
        // Invariant: some peak of the whole array lies in [low, high].
        int low = 0;
        int high = nums.length - 1;
        while (low < high) {
            int middle = (low + high) >>> 1;
            if (nums[middle] < nums[middle + 1]) {
                low = middle + 1;
            } else {
                high = middle;
            }
        }
        return low;
    }
}
