class Solution {
    fun canPartition(nums: IntArray): Boolean {
        val total = nums.sum()
        if (total % 2 == 1) return false
        val target = total / 2
        // reachable[s] is true when some of the elements seen so far add up to exactly s.
        val reachable = BooleanArray(target + 1)
        reachable[0] = true
        for (value in nums) {
            // Right to left, so reachable[s - value] still describes the elements before value.
            for (s in target downTo value) {
                if (reachable[s - value]) reachable[s] = true
            }
            if (reachable[target]) return true
        }
        return reachable[target]
    }
}
