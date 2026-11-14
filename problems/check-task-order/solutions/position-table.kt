class Solution {
    fun isValidTaskOrder(n: Int, prerequisites: Array<IntArray>, order: IntArray): Boolean {
        if (order.size != n) return false
        // position[t]: where task t stands in the order, or -1 while it has not been seen.
        val position = IntArray(n) { -1 }
        for ((place, task) in order.withIndex()) {
            if (position[task] != -1) return false
            position[task] = place
        }
        return prerequisites.all { (before, after) -> position[before] < position[after] }
    }
}
