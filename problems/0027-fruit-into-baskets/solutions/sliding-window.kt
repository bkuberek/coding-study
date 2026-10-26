class Solution {
    fun totalFruit(fruits: IntArray): Int {
        val inWindow = HashMap<Int, Int>()
        var left = 0
        var best = 0
        for (right in fruits.indices) {
            inWindow.merge(fruits[right], 1, Int::plus)
            while (inWindow.size > 2) {
                val leaving = fruits[left++]
                if (inWindow.merge(leaving, -1, Int::plus) == 0) inWindow.remove(leaving)
            }
            best = maxOf(best, right - left + 1)
        }
        return best
    }
}
