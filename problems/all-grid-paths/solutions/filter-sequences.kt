class Solution {
    fun allGridPaths(n: Int): List<String> {
        val steps = 2 * (n - 1)
        val paths = mutableListOf<String>()
        // Counting up from 0 reads the bits from the most significant one as the first move,
        // with 0 for D and 1 for R, so the sequences come out in lexicographic order.
        for (pattern in 0 until (1 shl steps)) {
            val moves = StringBuilder(steps)
            var rights = 0
            for (step in 0 until steps) {
                val isRight = (pattern shr (steps - 1 - step)) and 1
                moves.append(if (isRight == 1) 'R' else 'D')
                rights += isRight
            }
            if (rights == n - 1) {
                paths.add(moves.toString())
            }
        }
        return paths
    }
}
