class Solution {
    fun canCompleteCircuit(gas: IntArray, cost: IntArray): Int {
        val n = gas.size
        for (start in 0 until n) {
            var fuel = 0
            var step = 0
            while (step < n) {
                val station = (start + step) % n
                fuel += gas[station] - cost[station]
                if (fuel < 0) break
                step++
            }
            if (step == n) return start
        }
        return -1
    }
}
