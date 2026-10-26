class Solution {
    fun findMedianSortedArrays(nums1: IntArray, nums2: IntArray): Double {
        if (nums1.size > nums2.size) {
            return findMedianSortedArrays(nums2, nums1)
        }
        val total = nums1.size + nums2.size
        val lowerSize = (total + 1) / 2
        var low = 0
        var high = nums1.size
        while (low <= high) {
            // Take `take1` values from nums1 and the rest of the lower half from nums2.
            val take1 = (low + high) ushr 1
            val take2 = lowerSize - take1
            // Values are at most 10^6 in magnitude, so the Int extremes act as infinities.
            val left1 = if (take1 > 0) nums1[take1 - 1] else Int.MIN_VALUE
            val right1 = if (take1 < nums1.size) nums1[take1] else Int.MAX_VALUE
            val left2 = if (take2 > 0) nums2[take2 - 1] else Int.MIN_VALUE
            val right2 = if (take2 < nums2.size) nums2[take2] else Int.MAX_VALUE
            when {
                left1 > right2 -> high = take1 - 1
                left2 > right1 -> low = take1 + 1
                else -> {
                    val lowerMax = maxOf(left1, left2)
                    return if (total % 2 == 1) {
                        lowerMax.toDouble()
                    } else {
                        (lowerMax.toLong() + minOf(right1, right2)) / 2.0
                    }
                }
            }
        }
        throw IllegalArgumentException("the arrays must be sorted")
    }
}
