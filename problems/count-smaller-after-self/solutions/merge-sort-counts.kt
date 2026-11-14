class Solution {
    fun countSmaller(nums: IntArray): IntArray {
        val n = nums.size
        val counts = IntArray(n)
        var order = IntArray(n) { it } // positions, sorted by value within each merged run
        var buffer = IntArray(n)
        // Bottom-up merge sort of positions by value; no recursion needed.
        var width = 1
        while (width < n) {
            for (low in 0 until n step 2 * width) {
                val middle = minOf(low + width, n)
                val high = minOf(low + 2 * width, n)
                var left = low
                var right = middle
                var out = low
                while (left < middle) {
                    if (right < high && nums[order[right]] < nums[order[left]]) {
                        buffer[out++] = order[right++]
                    } else {
                        // Every right-half element taken so far is smaller and came after it.
                        counts[order[left]] += right - middle
                        buffer[out++] = order[left++]
                    }
                }
                while (right < high) buffer[out++] = order[right++]
            }
            order = buffer.also { buffer = order }
            width *= 2
        }
        return counts
    }
}
