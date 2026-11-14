class Solution {
    fun carFleet(target: Int, position: IntArray, speed: IntArray): Int {
        // Arrival times are distance / speed; compare them by cross-multiplying, so no division.
        fun arrivesLater(a: Int, b: Int): Boolean =
            (target - position[a]) * speed[b] > (target - position[b]) * speed[a]

        var fleets = 0
        for (car in position.indices) {
            var slowest = -1
            for (other in position.indices) {
                if (position[other] > position[car] && (slowest < 0 || arrivesLater(other, slowest))) {
                    slowest = other
                }
            }
            // The car leads its own fleet only if it arrives strictly later than the slowest car ahead.
            if (slowest < 0 || arrivesLater(car, slowest)) {
                fleets++
            }
        }
        return fleets
    }
}
