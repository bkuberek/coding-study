import java.util.PriorityQueue

class Solution {
    fun topKFrequent(nums: IntArray, k: Int): IntArray {
        val counts = HashMap<Int, Int>()
        for (value in nums) {
            counts[value] = counts.getOrDefault(value, 0) + 1
        }
        // PriorityQueue is a min-heap: its head is the weakest of the k values kept so far.
        val heap = PriorityQueue<Int>(compareBy { counts.getValue(it) })
        for ((value, count) in counts) {
            if (heap.size < k) {
                heap.offer(value)
            } else if (count > counts.getValue(heap.peek())) {
                heap.poll()
                heap.offer(value)
            }
        }
        return heap.toIntArray()
    }
}
