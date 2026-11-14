class Solution {
    fun minEatingSpeed(piles: IntArray, h: Int): Int =
        generateSequence(1) { it + 1 }.first { speed -> hoursAt(piles, speed) <= h }

    private fun hoursAt(piles: IntArray, speed: Int): Long =
        piles.sumOf { pile -> (pile + speed - 1L) / speed }
}
