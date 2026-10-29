class Solution {
    private companion object {
        const val MODULUS = 1_000_000_007L
    }

    fun createSortedArray(instructions: IntArray): Int {
        val largest = instructions.max()
        // tree[i] (1-based) counts the inserted values in (i - lowBit(i), i].
        val tree = IntArray(largest + 1)

        fun countAtMost(value: Int): Int {
            var total = 0
            var i = value
            while (i > 0) {
                total += tree[i]
                i -= i and -i
            }
            return total
        }

        var cost = 0L
        for ((inserted, value) in instructions.withIndex()) {
            val less = countAtMost(value - 1)
            val greater = inserted - countAtMost(value)
            cost = (cost + minOf(less, greater)) % MODULUS
            var i = value
            while (i <= largest) {
                tree[i]++
                i += i and -i
            }
        }
        return cost.toInt()
    }
}
