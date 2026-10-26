class Solution {
    fun findMedianSortedArrays(nums1: IntArray, nums2: IntArray): Double {
        val total = nums1.size + nums2.size
        var i = 0
        var j = 0
        var previous = 0
        var current = 0
        // Advance through the merged order until `current` is the value at position total / 2.
        repeat(total / 2 + 1) {
            previous = current
            current = if (j == nums2.size || (i < nums1.size && nums1[i] <= nums2[j])) {
                nums1[i++]
            } else {
                nums2[j++]
            }
        }
        return if (total % 2 == 1) current.toDouble() else (previous + current) / 2.0
    }
}
