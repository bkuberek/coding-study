class Solution {
    fun findTargetSumWays(nums: IntArray, target: Int): Int {
        val total = nums.sum()
        // ways[index][running + total] caches the count from that state; -1 is unknown.
        val ways = Array(nums.size) { IntArray(2 * total + 1) { -1 } }

        fun count(index: Int, running: Int): Int {
            if (index == nums.size) return if (running == target) 1 else 0
            val offset = running + total
            if (ways[index][offset] < 0) {
                ways[index][offset] = count(index + 1, running + nums[index]) + count(index + 1, running - nums[index])
            }
            return ways[index][offset]
        }

        return count(0, 0)
    }
}
