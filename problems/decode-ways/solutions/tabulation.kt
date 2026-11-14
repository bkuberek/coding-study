class Solution {
    fun numDecodings(s: String): Int {
        // ways[i] is the number of readings of the prefix s[0 until i]; the empty prefix has one.
        val ways = IntArray(s.length + 1)
        ways[0] = 1
        for (i in 1..s.length) {
            if (s[i - 1] != '0') ways[i] += ways[i - 1]
            if (i >= 2 && s.substring(i - 2, i).toInt() in 10..26) ways[i] += ways[i - 2]
        }
        return ways[s.length]
    }
}
