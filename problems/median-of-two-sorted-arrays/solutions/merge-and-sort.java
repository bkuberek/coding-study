import java.util.*;

public class Solution {
    public double findMedianSortedArrays(int[] nums1, int[] nums2) {
        int[] merged = Arrays.copyOf(nums1, nums1.length + nums2.length);
        System.arraycopy(nums2, 0, merged, nums1.length, nums2.length);
        Arrays.sort(merged);
        int middle = merged.length / 2;
        if (merged.length % 2 == 1) {
            return merged[middle];
        }
        return (merged[middle - 1] + merged[middle]) / 2.0;
    }
}
