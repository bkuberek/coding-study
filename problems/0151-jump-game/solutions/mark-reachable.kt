class Solution {
    fun canJump(nums: IntArray): Boolean {
        val last = nums.size - 1
        // reachable[i] is true once some sequence of jumps from index 0 is known to land on i.
        val reachable = BooleanArray(nums.size)
        reachable[0] = true
        for (i in nums.indices) {
            if (!reachable[i]) continue
            if (i == last) return true
            for (target in i + 1..minOf(last, i + nums[i])) reachable[target] = true
        }
        return reachable[last]
    }
}
