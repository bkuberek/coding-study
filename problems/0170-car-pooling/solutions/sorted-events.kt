class Solution {
    fun carPooling(trips: Array<IntArray>, capacity: Int): Boolean {
        val events = ArrayList<IntArray>(2 * trips.size)
        for ((passengers, start, end) in trips) {
            events.add(intArrayOf(start, passengers))
            events.add(intArrayOf(end, -passengers))
        }
        // By location, then by change: drop-offs (negative) come before pickups at the same place.
        events.sortWith(compareBy<IntArray>({ it[0] }, { it[1] }))
        var load = 0
        for ((_, change) in events) {
            load += change
            if (load > capacity) return false
        }
        return true
    }
}
