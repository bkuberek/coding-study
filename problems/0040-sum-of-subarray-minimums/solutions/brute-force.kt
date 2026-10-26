private const val MOD = 1_000_000_007L

class Solution {
    fun sumSubarrayMins(arr: IntArray): Int {
        var total = 0L
        for (start in arr.indices) {
            var minimum = arr[start]
            for (end in start until arr.size) {
                minimum = minOf(minimum, arr[end])
                total += minimum
            }
            total %= MOD
        }
        return total.toInt()
    }
}
