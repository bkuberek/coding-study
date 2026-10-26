class Solution {
    fun totalFruit(fruits: IntArray): Int {
        var best = 0
        for (start in fruits.indices) {
            val first = fruits[start]
            var second = -1
            var end = start
            while (end < fruits.size) {
                val fruit = fruits[end]
                if (fruit != first && fruit != second) {
                    if (second != -1) break
                    second = fruit
                }
                end++
            }
            best = maxOf(best, end - start)
        }
        return best
    }
}
