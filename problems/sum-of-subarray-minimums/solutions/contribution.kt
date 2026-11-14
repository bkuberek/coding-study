private const val MOD = 1_000_000_007L

class Solution {
    fun sumSubarrayMins(arr: IntArray): Int {
        var total = 0L
        // Indexes whose values strictly increase from bottom to top.
        val stack = ArrayDeque<Int>()
        // One extra step with value 0, below every element, pops whatever is left.
        for (index in 0..arr.size) {
            val value = if (index < arr.size) arr[index] else 0
            while (stack.isNotEmpty() && arr[stack.last()] >= value) {
                val middle = stack.removeLast()
                // Starts after the previous strictly smaller element, ends before the next
                // smaller-or-equal one (index): arr[middle] is the minimum of left * right subarrays.
                val left = (middle - (stack.lastOrNull() ?: -1)).toLong()
                val right = (index - middle).toLong()
                total = (total + arr[middle] * left * right) % MOD
            }
            stack.addLast(index)
        }
        return total.toInt()
    }
}
