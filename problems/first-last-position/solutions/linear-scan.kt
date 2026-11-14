class Solution {
    fun searchRange(nums: IntArray, target: Int): IntArray =
        intArrayOf(nums.indexOfFirst { it == target }, nums.indexOfLast { it == target })
}
