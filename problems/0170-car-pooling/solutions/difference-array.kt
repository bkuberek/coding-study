class Solution {
    fun carPooling(trips: Array<IntArray>, capacity: Int): Boolean {
        val last = trips.maxOf { it[2] }
        // change[x] is how much the load changes at location x; its prefix sums are the loads.
        val change = IntArray(last + 1)
        for ((passengers, start, end) in trips) {
            change[start] += passengers
            change[end] -= passengers
        }
        var load = 0
        for (delta in change) {
            load += delta
            if (load > capacity) return false
        }
        return true
    }
}
