public class Solution {
    public double findMedianSortedArrays(int[] nums1, int[] nums2) {
        if (nums1.length > nums2.length) {
            return findMedianSortedArrays(nums2, nums1);
        }
        int total = nums1.length + nums2.length;
        int lowerSize = (total + 1) / 2;
        int low = 0;
        int high = nums1.length;
        while (low <= high) {
            // Take `take1` values from nums1 and the rest of the lower half from nums2.
            int take1 = (low + high) >>> 1;
            int take2 = lowerSize - take1;
            // Values are at most 10^6 in magnitude, so the int extremes act as infinities.
            int left1 = take1 > 0 ? nums1[take1 - 1] : Integer.MIN_VALUE;
            int right1 = take1 < nums1.length ? nums1[take1] : Integer.MAX_VALUE;
            int left2 = take2 > 0 ? nums2[take2 - 1] : Integer.MIN_VALUE;
            int right2 = take2 < nums2.length ? nums2[take2] : Integer.MAX_VALUE;
            if (left1 > right2) {
                high = take1 - 1;
            } else if (left2 > right1) {
                low = take1 + 1;
            } else {
                int lowerMax = Math.max(left1, left2);
                if (total % 2 == 1) {
                    return lowerMax;
                }
                return ((long) lowerMax + Math.min(right1, right2)) / 2.0;
            }
        }
        throw new IllegalArgumentException("the arrays must be sorted");
    }
}
