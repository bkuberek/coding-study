class Solution {
    fun countBits(n: Int): IntArray = IntArray(n + 1) { i ->
        var word = i
        var count = 0
        while (word != 0) {
            word = word and (word - 1) // clears the lowest set bit
            count++
        }
        count
    }
}
