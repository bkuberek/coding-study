private const val START = "0000"

/** The eight settings one move away: each wheel up or down by one, wrapping around. */
private fun turns(setting: String): List<String> {
    val result = ArrayList<String>(8)
    val wheels = setting.toCharArray()
    for (wheel in 0 until 4) {
        val original = wheels[wheel]
        for (turn in intArrayOf(1, 9)) {
            wheels[wheel] = '0' + (original - '0' + turn) % 10
            result.add(String(wheels))
        }
        wheels[wheel] = original
    }
    return result
}

class Solution {
    fun openLock(deadends: Array<String>, target: String): Int {
        // Dead ends behave like settings that were already visited: the search never enters them.
        val seen = deadends.toHashSet()
        if (START in seen) return -1
        seen.add(START)
        var level = listOf(START)
        var moves = 0
        while (level.isNotEmpty()) {
            if (target in level) return moves
            level = level.flatMap(::turns).filter(seen::add)
            moves++
        }
        return -1
    }
}
