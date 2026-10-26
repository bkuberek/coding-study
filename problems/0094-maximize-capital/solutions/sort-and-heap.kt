import java.util.PriorityQueue

class Solution {
    fun findMaximizedCapital(k: Int, w: Int, profits: IntArray, capital: IntArray): Int {
        val order = profits.indices.sortedBy { capital[it] } // cheapest requirement first
        val affordable = PriorityQueue<Int>(reverseOrder())
        var funds = w
        var unlocked = 0
        repeat(k) {
            // Capital only grows, so every project unlocked once stays affordable.
            while (unlocked < order.size && capital[order[unlocked]] <= funds) {
                affordable.offer(profits[order[unlocked++]])
            }
            // Nothing affordable now, and capital cannot grow any more.
            val best = affordable.poll() ?: return funds
            funds += best
        }
        return funds
    }
}
