import java.util.PriorityQueue

class Solution {
    fun kClosest(points: Array<IntArray>, k: Int): Array<IntArray> {
        fun squared(index: Int): Int = points[index].let { (x, y) -> x * x + y * y }
        // Indexes ordered by decreasing distance: the head is the farthest of the k kept.
        val heap = PriorityQueue<Int>(compareByDescending(::squared))
        for (index in points.indices) {
            if (heap.size < k) {
                heap.offer(index)
            } else if (squared(index) < squared(heap.peek())) {
                heap.poll()
                heap.offer(index)
            }
        }
        return heap.map { points[it] }.toTypedArray()
    }
}
