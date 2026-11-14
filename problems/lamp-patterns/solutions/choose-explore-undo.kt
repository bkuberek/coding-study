class Solution {
    fun lampPatterns(n: Int): List<String> {
        val result = mutableListOf<String>()
        val lamps = StringBuilder(n)

        fun extend() {
            if (lamps.length == n) {
                result.add(lamps.toString())
                return
            }
            lamps.append('0') // choose: off
            extend() // explore
            lamps.deleteCharAt(lamps.length - 1) // undo
            // Prune: a lamp may be on only when its left neighbour is off (or missing).
            if (lamps.isEmpty() || lamps.last() == '0') {
                lamps.append('1')
                extend()
                lamps.deleteCharAt(lamps.length - 1)
            }
        }

        extend()
        return result
    }
}
