class Solution {
    fun candy(ratings: IntArray): Int {
        var total = 1
        var up = 0 // length of the current rising run: the latest child got up + 1 candies
        var down = 0 // length of the current falling run
        var peak = 0 // the rising run length at the top of the current peak
        for (i in 1 until ratings.size) {
            when {
                ratings[i] > ratings[i - 1] -> {
                    up++
                    peak = up
                    down = 0
                    total += up + 1
                }
                ratings[i] == ratings[i - 1] -> {
                    up = 0
                    down = 0
                    peak = 0
                    total += 1
                }
                else -> {
                    up = 0
                    down++
                    // Every child on the falling run gets one more candy; the peak only needs
                    // one more once the falling run is longer than the rising run that built it.
                    total += down + if (down > peak) 1 else 0
                }
            }
        }
        return total
    }
}
