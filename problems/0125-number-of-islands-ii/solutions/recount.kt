private val STEPS = arrayOf(intArrayOf(1, 0), intArrayOf(-1, 0), intArrayOf(0, 1), intArrayOf(0, -1))

class Solution {
    fun numIslands2(m: Int, n: Int, positions: Array<IntArray>): IntArray {
        val land = BooleanArray(m * n) // cell r * n + c
        val cells = mutableListOf<Int>() // every land cell, each once
        // seenInRound[cell] == round marks a cell visited by the current recount, so the
        // array is allocated once instead of once per operation.
        val seenInRound = IntArray(m * n)
        val stack = ArrayDeque<Int>()

        fun countIslands(round: Int): Int {
            var islands = 0
            for (start in cells) {
                if (seenInRound[start] == round) continue
                islands++
                seenInRound[start] = round
                stack.addLast(start)
                while (stack.isNotEmpty()) {
                    val cell = stack.removeLast()
                    for ((dr, dc) in STEPS) {
                        val nr = cell / n + dr
                        val nc = cell % n + dc
                        val neighbor = nr * n + nc
                        if (nr in 0 until m && nc in 0 until n && land[neighbor] && seenInRound[neighbor] != round) {
                            seenInRound[neighbor] = round
                            stack.addLast(neighbor)
                        }
                    }
                }
            }
            return islands
        }

        return IntArray(positions.size) { i ->
            val (r, c) = positions[i]
            if (!land[r * n + c]) {
                land[r * n + c] = true
                cells.add(r * n + c)
            }
            countIslands(i + 1)
        }
    }
}
