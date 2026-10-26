class Solution {
    fun canCompleteCircuit(gas: IntArray, cost: IntArray): Int {
        // balance is the fuel after driving from station 0 past `station` (it may go negative).
        // Starting right after the station where it is lowest lifts every point of the trip to
        // at least zero, provided the whole circle does not lose fuel.
        var balance = 0
        var lowest = 0
        var start = 0
        for (station in gas.indices) {
            balance += gas[station] - cost[station]
            if (balance < lowest) {
                lowest = balance
                start = station + 1
            }
        }
        return if (balance < 0) -1 else start % gas.size
    }
}
