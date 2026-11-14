class Solution {
    fun candy(ratings: IntArray): Int {
        val n = ratings.size
        val candies = IntArray(n) { 1 }
        // Left to right: the fewest candies that respect every left neighbor.
        for (i in 1 until n) {
            if (ratings[i] > ratings[i - 1]) candies[i] = candies[i - 1] + 1
        }
        // Right to left: also respect every right neighbor, without undoing the first pass.
        for (i in n - 2 downTo 0) {
            if (ratings[i] > ratings[i + 1]) candies[i] = maxOf(candies[i], candies[i + 1] + 1)
        }
        return candies.sum()
    }
}
