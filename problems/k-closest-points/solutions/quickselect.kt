import kotlin.random.Random

class Solution {
    fun kClosest(points: Array<IntArray>, k: Int): Array<IntArray> {
        val distance = IntArray(points.size) { points[it].let { (x, y) -> x * x + y * y } }
        val order = IntArray(points.size) { it }
        var low = 0
        var high = order.lastIndex
        // Partition until position k - 1 holds its sorted entry; then positions 0..k-1 hold
        // the k closest points (in some order).
        while (low < high) {
            val pivot = distance[order[Random.nextInt(low, high + 1)]]
            var less = low
            var scan = low
            var greater = high
            while (scan <= greater) {
                val value = distance[order[scan]]
                when {
                    value < pivot -> order.swap(less++, scan++)
                    value > pivot -> order.swap(scan, greater--)
                    else -> scan++
                }
            }
            when {
                k - 1 < less -> high = less - 1
                k - 1 > greater -> low = greater + 1
                else -> break
            }
        }
        return Array(k) { points[order[it]] }
    }

    private fun IntArray.swap(i: Int, j: Int) {
        val held = this[i]
        this[i] = this[j]
        this[j] = held
    }
}
