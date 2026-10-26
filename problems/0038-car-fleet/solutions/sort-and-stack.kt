class Solution {
    fun carFleet(target: Int, position: IntArray, speed: IntArray): Int {
        // Fleets formed so far, from the farthest back (bottom) to the closest to the target (top);
        // their arrival times strictly decrease from bottom to top.
        val fleets = ArrayDeque<Double>()
        for (car in position.indices.sortedBy { position[it] }) {
            val arrival = (target - position[car]).toDouble() / speed[car]
            // Every fleet behind this car that would arrive no later catches up with it.
            while (fleets.isNotEmpty() && fleets.last() <= arrival) {
                fleets.removeLast()
            }
            fleets.addLast(arrival)
        }
        return fleets.size
    }
}
