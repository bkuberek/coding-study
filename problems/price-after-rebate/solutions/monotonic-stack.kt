class Solution {
    fun pricesAfterRebate(prices: IntArray): IntArray {
        val paid = prices.copyOf()
        // Slots still waiting for a rebate; their prices rise strictly from bottom to top.
        val waiting = ArrayDeque<Int>()
        for ((slot, price) in prices.withIndex()) {
            while (waiting.isNotEmpty() && prices[waiting.last()] >= price) {
                val earlier = waiting.removeLast()
                paid[earlier] = prices[earlier] - price
            }
            waiting.addLast(slot)
        }
        return paid
    }
}
