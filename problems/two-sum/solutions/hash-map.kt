class Solution {
    fun twoSum(nums: IntArray, target: Int): IntArray {
        val indexByValue = HashMap<Int, Int>()
        for ((i, value) in nums.withIndex()) {
            indexByValue[target - value]?.let { partner -> return intArrayOf(partner, i) }
            indexByValue[value] = i
        }
        return intArrayOf()
    }
}
