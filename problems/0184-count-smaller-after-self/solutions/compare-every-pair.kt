class Solution {
    fun countSmaller(nums: IntArray): IntArray = IntArray(nums.size) { i ->
        var smaller = 0
        for (j in i + 1 until nums.size) {
            if (nums[j] < nums[i]) smaller++
        }
        smaller
    }
}
