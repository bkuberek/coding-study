import java.util.PriorityQueue

class Solution {
    fun lastStoneWeight(stones: IntArray): Int {
        // PriorityQueue is a min-heap; the reversed comparator turns it into a max-heap.
        val heap = PriorityQueue<Int>(maxOf(1, stones.size), reverseOrder())
        stones.forEach(heap::offer)
        while (heap.size > 1) {
            val heaviest = heap.poll()
            val second = heap.poll()
            if (heaviest != second) heap.offer(heaviest - second)
        }
        return heap.peek() ?: 0
    }
}
