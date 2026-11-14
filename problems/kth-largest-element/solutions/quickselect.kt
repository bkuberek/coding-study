import kotlin.random.Random

class Solution {
    fun findKthLargest(nums: IntArray, k: Int): Int {
        val values = nums.copyOf()
        val target = values.size - k // the answer's index in ascending order
        var low = 0
        var high = values.lastIndex
        while (true) {
            val pivot = values[Random.nextInt(low, high + 1)]
            // Three-way partition of values[low..high]: < pivot | == pivot | > pivot.
            var less = low
            var scan = low
            var greater = high
            while (scan <= greater) {
                when {
                    values[scan] < pivot -> values.swap(less++, scan++)
                    values[scan] > pivot -> values.swap(scan, greater--)
                    else -> scan++
                }
            }
            when {
                target < less -> high = less - 1
                target > greater -> low = greater + 1
                else -> return pivot
            }
        }
    }

    private fun IntArray.swap(i: Int, j: Int) {
        val held = this[i]
        this[i] = this[j]
        this[j] = held
    }
}
