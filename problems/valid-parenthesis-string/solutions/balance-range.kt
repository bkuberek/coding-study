class Solution {
    fun checkValidString(s: String): Boolean {
        // The possible open counts of the prefix are exactly the integers in [lowest, highest].
        var lowest = 0
        var highest = 0
        for (c in s) {
            when (c) {
                '(' -> { lowest++; highest++ }
                ')' -> { lowest--; highest-- }
                else -> { lowest--; highest++ } // the wildcard as ")" or as "("
            }
            if (highest < 0) return false // even with every wildcard as "(", too many ")"
            lowest = maxOf(lowest, 0) // a negative count is not a real choice
        }
        return lowest == 0
    }
}
