class Solution {
    private companion object {
        const val MODULUS = 1_000_000_007L
    }

    fun createSortedArray(instructions: IntArray): Int {
        val ordered = ArrayList<Int>()
        var cost = 0L // a Long: the total can pass Int.MAX_VALUE before the final reduction
        for (value in instructions) {
            val less = countBelow(ordered, value, inclusive = false)
            val lessOrEqual = countBelow(ordered, value, inclusive = true)
            cost += minOf(less, ordered.size - lessOrEqual)
            ordered.add(lessOrEqual, value)
        }
        return (cost % MODULUS).toInt()
    }

    /** How many values of the sorted list are below [target] (or at most [target], if [inclusive]). */
    private fun countBelow(sorted: List<Int>, target: Int, inclusive: Boolean): Int {
        var low = 0
        var high = sorted.size
        while (low < high) {
            val middle = low + (high - low) / 2
            val value = sorted[middle]
            if (value < target || (inclusive && value == target)) {
                low = middle + 1
            } else {
                high = middle
            }
        }
        return low
    }
}
