import java.util.PriorityQueue

class KthLargestTracker(private val k: Int, nums: IntArray) {
    // The k largest numbers seen so far. PriorityQueue keeps the least element at its head.
    private val top = PriorityQueue<Int>()

    init {
        for (value in nums) offer(value)
    }

    fun add(value: Int): Int {
        offer(value)
        return top.peek()
    }

    private fun offer(value: Int) {
        top.offer(value)
        // k + 1 numbers are in the heap; the smallest cannot be among the k largest.
        if (top.size > k) top.poll()
    }
}
