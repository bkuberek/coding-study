class Solution {
    fun dailyTemperatures(temperatures: IntArray): IntArray {
        val days = temperatures.size
        val waits = IntArray(days)
        for (day in 0 until days) {
            for (later in day + 1 until days) {
                if (temperatures[later] > temperatures[day]) {
                    waits[day] = later - day
                    break
                }
            }
        }
        return waits
    }
}
