class Solution {
    fun sortColors(nums: IntArray) {
        val counts = IntArray(3)
        for (color in nums) {
            counts[color]++
        }
        nums.fill(0, 0, counts[0])
        nums.fill(1, counts[0], counts[0] + counts[1])
        nums.fill(2, counts[0] + counts[1])
    }
}
