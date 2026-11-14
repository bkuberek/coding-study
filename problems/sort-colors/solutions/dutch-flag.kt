class Solution {
    fun sortColors(nums: IntArray) {
        var low = 0
        var mid = 0
        var high = nums.size - 1
        while (mid <= high) {
            when (nums[mid]) {
                0 -> nums.swap(low++, mid++)
                1 -> mid++
                else -> nums.swap(mid, high--)
            }
        }
    }

    private fun IntArray.swap(i: Int, j: Int) {
        this[i] = this[j].also { this[j] = this[i] }
    }
}
