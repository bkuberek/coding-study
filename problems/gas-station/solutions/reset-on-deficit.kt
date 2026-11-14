class Solution {
    fun canCompleteCircuit(gas: IntArray, cost: IntArray): Int {
        var total = 0 // fuel balance of the whole circle
        var fuel = 0 // fuel since the current candidate start
        var start = 0
        for (station in gas.indices) {
            val surplus = gas[station] - cost[station]
            total += surplus
            fuel += surplus
            if (fuel < 0) {
                // No station from `start` to `station` can be the answer; try the next one.
                start = station + 1
                fuel = 0
            }
        }
        return if (total >= 0) start else -1
    }
}
