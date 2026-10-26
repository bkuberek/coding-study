private const val UNKNOWN: Byte = 0
private const val YES: Byte = 1
private const val NO: Byte = 2

class Solution {
    fun canPartition(nums: IntArray): Boolean {
        val total = nums.sum()
        if (total % 2 == 1) return false
        // memo[index][remaining] answers "can nums[index..] add up to exactly remaining?".
        val memo = Array(nums.size) { ByteArray(total / 2 + 1) }

        fun reachable(index: Int, remaining: Int): Boolean {
            if (remaining == 0) return true
            if (index == nums.size || remaining < 0) return false
            if (memo[index][remaining] == UNKNOWN) {
                val found = reachable(index + 1, remaining - nums[index]) ||
                    reachable(index + 1, remaining)
                memo[index][remaining] = if (found) YES else NO
            }
            return memo[index][remaining] == YES
        }

        return reachable(0, total / 2)
    }
}
