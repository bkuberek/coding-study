public class Solution {
    public int findPeakElement(int[] nums) {
        // Before the first descent the values only rise, so the element just before it beats
        // both neighbors. With no descent at all, the last element is the peak.
        for (int i = 0; i < nums.length - 1; i++) {
            if (nums[i] > nums[i + 1]) {
                return i;
            }
        }
        return nums.length - 1;
    }
}
