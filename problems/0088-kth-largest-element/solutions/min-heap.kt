import java.util.PriorityQueue

class Solution {
    fun findKthLargest(nums: IntArray, k: Int): Int {
        // The heap keeps the k largest values seen so far; its head is the smallest of them.
        val heap = PriorityQueue<Int>(k)
        for (value in nums) {
            if (heap.size < k) {
                heap.offer(value)
            } else if (value > heap.peek()) {
                heap.poll()
                heap.offer(value)
            }
        }
        return heap.peek()
    }
}
