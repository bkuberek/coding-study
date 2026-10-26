class Solution {
    fun candy(ratings: IntArray): Int {
        val n = ratings.size
        val candies = IntArray(n) { 1 }
        var changed = true
        while (changed) {
            // Raise any child who does not have more than a lower-rated neighbor; repeat until
            // no rule is violated. Counts only grow, and each raise is the least that fixes it.
            changed = false
            for (i in 0 until n) {
                if (i > 0 && ratings[i] > ratings[i - 1] && candies[i] <= candies[i - 1]) {
                    candies[i] = candies[i - 1] + 1
                    changed = true
                }
                if (i < n - 1 && ratings[i] > ratings[i + 1] && candies[i] <= candies[i + 1]) {
                    candies[i] = candies[i + 1] + 1
                    changed = true
                }
            }
        }
        return candies.sum()
    }
}
