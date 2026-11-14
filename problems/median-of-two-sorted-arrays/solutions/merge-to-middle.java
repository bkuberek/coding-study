public class Solution {
    public double findMedianSortedArrays(int[] nums1, int[] nums2) {
        int total = nums1.length + nums2.length;
        int i = 0;
        int j = 0;
        int previous = 0;
        int current = 0;
        // Advance through the merged order until `current` is the value at position total / 2.
        for (int step = 0; step <= total / 2; step++) {
            previous = current;
            if (j == nums2.length || (i < nums1.length && nums1[i] <= nums2[j])) {
                current = nums1[i++];
            } else {
                current = nums2[j++];
            }
        }
        return total % 2 == 1 ? current : (previous + current) / 2.0;
    }
}
