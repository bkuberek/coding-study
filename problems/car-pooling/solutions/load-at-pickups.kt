class Solution {
    fun carPooling(trips: Array<IntArray>, capacity: Int): Boolean {
        // The load is highest right after some pickup, so checking every pickup point suffices.
        val busiest = trips.maxOf { booking ->
            val pickup = booking[1]
            trips.sumOf { (passengers, start, end) -> if (pickup in start until end) passengers else 0 }
        }
        return busiest <= capacity
    }
}
