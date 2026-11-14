class Solution {
    fun leastInterval(tasks: CharArray, cooldown: Int): Int {
        val counts = IntArray(26)
        for (task in tasks) counts[task - 'A']++
        val top = counts.max()
        val tied = counts.count { it == top }
        // top - 1 full frames of cooldown + 1 slots, then one last partial frame holding the
        // tied most frequent tasks. With enough other tasks, no slot idles.
        return maxOf(tasks.size, (top - 1) * (cooldown + 1) + tied)
    }
}
