class Solution {
    fun findMedianSortedArrays(nums1: IntArray, nums2: IntArray): Double {
        val merged = (nums1 + nums2).apply { sort() }
        val middle = merged.size / 2
        return if (merged.size % 2 == 1) {
            merged[middle].toDouble()
        } else {
            (merged[middle - 1] + merged[middle]) / 2.0
        }
    }
}
