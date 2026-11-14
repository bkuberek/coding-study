class Solution {
    fun checkSubarraySum(nums: IntArray, k: Int): Boolean {
        // firstIndex maps a prefix remainder to the earliest position where it appeared;
        // the empty prefix ends at position -1.
        val firstIndex = HashMap<Int, Int>()
        firstIndex[0] = -1
        var remainder = 0
        for ((position, value) in nums.withIndex()) {
            // remainder + value can pass Int.MAX_VALUE, so add in Long before reducing.
            remainder = ((remainder.toLong() + value) % k).toInt()
            val earlier = firstIndex.putIfAbsent(remainder, position)
            if (earlier != null && position - earlier >= 2) return true
        }
        return false
    }
}
