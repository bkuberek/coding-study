class Solution {
    fun moveZeroes(nums: IntArray) {
        val nonZero = nums.filter { it != 0 }
        nonZero.forEachIndexed { index, value -> nums[index] = value }
        nums.fill(0, nonZero.size)
    }
}
