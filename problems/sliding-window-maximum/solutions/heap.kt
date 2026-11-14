import java.util.PriorityQueue

class Solution {
    fun maxSlidingWindow(nums: IntArray, k: Int): IntArray {
        val heap = PriorityQueue<Int>(compareByDescending { nums[it] })
        val maxima = IntArray(nums.size - k + 1)
        for (right in nums.indices) {
            heap.add(right)
            if (right >= k - 1) {
                while (heap.peek() <= right - k) heap.poll()
                maxima[right - k + 1] = nums[heap.peek()]
            }
        }
        return maxima
    }
}
