class Solution {
    fun majorityElement(nums: IntArray): Int {
        val half = nums.size / 2
        val counts = HashMap<Int, Int>()
        for (value in nums) {
            val count = counts.getOrDefault(value, 0) + 1
            if (count > half) {
                return value
            }
            counts[value] = count
        }
        throw IllegalArgumentException("no majority element")
    }
}
