class Solution {
    fun dailyTemperatures(temperatures: IntArray): IntArray {
        val waits = IntArray(temperatures.size)
        // Days still waiting for a warmer day; their readings never rise from bottom to top.
        val waiting = ArrayDeque<Int>()
        for ((day, temperature) in temperatures.withIndex()) {
            while (waiting.isNotEmpty() && temperatures[waiting.last()] < temperature) {
                val earlier = waiting.removeLast()
                waits[earlier] = day - earlier
            }
            waiting.addLast(day)
        }
        return waits
    }
}
