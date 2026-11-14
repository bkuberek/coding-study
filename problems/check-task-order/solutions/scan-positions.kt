class Solution {
    fun isValidTaskOrder(n: Int, prerequisites: Array<IntArray>, order: IntArray): Boolean {
        if (order.size != n) return false
        for (task in 0 until n) {
            if (order.count { it == task } != 1) return false
        }
        for ((before, after) in prerequisites) {
            if (order.indexOf(before) >= order.indexOf(after)) return false
        }
        return true
    }
}
