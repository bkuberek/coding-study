class Solution {
    fun numOfMinutes(n: Int, headID: Int, manager: IntArray, informTime: IntArray): Int {
        var longest = 0
        for (employee in 0 until n) {
            // The news reaches employee after every manager above them has passed it on.
            var elapsed = 0
            var current = employee
            while (current != headID) {
                current = manager[current]
                elapsed += informTime[current]
            }
            longest = maxOf(longest, elapsed)
        }
        return longest
    }
}
