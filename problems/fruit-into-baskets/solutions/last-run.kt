class Solution {
    fun totalFruit(fruits: IntArray): Int {
        var best = 0
        var window = 0
        var last = -1
        var beforeLast = -1
        var lastRun = 0
        for (fruit in fruits) {
            window = if (fruit == last || fruit == beforeLast) window + 1 else lastRun + 1
            if (fruit == last) {
                lastRun++
            } else {
                beforeLast = last
                last = fruit
                lastRun = 1
            }
            best = maxOf(best, window)
        }
        return best
    }
}
