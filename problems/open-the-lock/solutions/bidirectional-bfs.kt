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
        val blocked = deadends.toHashSet()
        if (START in blocked) return -1
        if (target == START) return 0
        // Two frontiers grow toward each other; moves counts the levels expanded so far.
        var near = hashSetOf(START)
        var far = hashSetOf(target)
        val seen = hashSetOf(START, target)
        var moves = 0
        while (near.isNotEmpty() && far.isNotEmpty()) {
            if (near.size > far.size) near = far.also { far = near } // expand the smaller frontier
            moves++
            val next = HashSet<String>()
            for (setting in near) {
                for (following in turns(setting)) {
                    if (following in far) return moves
                    if (following !in blocked && seen.add(following)) next.add(following)
                }
            }
            near = next
        }
        return -1
    }
}
