private const val MOD = 1_000_000_007L

class Solution {
    fun sumSubarrayMins(arr: IntArray): Int {
        // ending[i] is the sum of the minimums of the subarrays that end at i (at most 9 * 10^8).
        val ending = LongArray(arr.size)
        // Indexes whose values strictly increase from bottom to top.
        val stack = ArrayDeque<Int>()
        var total = 0L
        for ((index, value) in arr.withIndex()) {
            while (stack.isNotEmpty() && arr[stack.last()] >= value) {
                stack.removeLast()
            }
            val previous = stack.lastOrNull()
            ending[index] = if (previous != null) {
                // Starts after the previous smaller element have minimum `value`; earlier starts
                // have the same minimums as the subarrays ending at `previous`.
                ending[previous] + value.toLong() * (index - previous)
            } else {
                value.toLong() * (index + 1)
            }
            stack.addLast(index)
            total = (total + ending[index]) % MOD
        }
        return total.toInt()
    }
}
