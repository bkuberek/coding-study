class Solution {
    fun canJump(nums: IntArray): Boolean {
        var farthest = 0 // every index up to `farthest` is reachable
        for (i in nums.indices) {
            if (i > farthest) return false
            farthest = maxOf(farthest, i + nums[i])
        }
        return true
    }
}
