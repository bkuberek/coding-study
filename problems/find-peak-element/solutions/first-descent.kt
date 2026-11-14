class Solution {
    fun findPeakElement(nums: IntArray): Int {
        // Before the first descent the values only rise, so the element just before it beats
        // both neighbors. With no descent at all, the last element is the peak.
        for (i in 0 until nums.lastIndex) {
            if (nums[i] > nums[i + 1]) {
                return i
            }
        }
        return nums.lastIndex
    }
}
