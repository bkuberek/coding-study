class Solution {
    fun minEatingSpeed(piles: IntArray, h: Int): Int {
        // Hours never increase with speed: find the first speed in [1, max(piles)] that fits.
        var low = 1
        var high = piles.max()
        while (low < high) {
            val speed = low + (high - low) / 2
            if (hoursAt(piles, speed) <= h) high = speed else low = speed + 1
        }
        return low
    }

    private fun hoursAt(piles: IntArray, speed: Int): Long =
        piles.sumOf { pile -> (pile + speed - 1L) / speed }
}
