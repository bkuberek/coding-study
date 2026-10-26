class Solution {
    fun climbStairs(n: Int): Int {
        // ways[step] counts the move sequences that end exactly on `step`.
        val ways = IntArray(n + 1)
        ways[0] = 1
        ways[1] = 1
        for (step in 2..n) {
            ways[step] = ways[step - 1] + ways[step - 2]
        }
        return ways[n]
    }
}
