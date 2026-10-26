class Solution {
    fun climbStairs(n: Int): Int {
        // Before each iteration: twoBelow and oneBelow count the ways to reach the two steps
        // just below the one being computed.
        var twoBelow = 1
        var oneBelow = 1
        repeat(n - 1) {
            val current = oneBelow + twoBelow
            twoBelow = oneBelow
            oneBelow = current
        }
        return oneBelow
    }
}
