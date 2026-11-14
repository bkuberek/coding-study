class Solution {
    fun allGridPaths(n: Int): List<String> {
        val last = n - 1
        val paths = mutableListOf<String>()
        val moves = StringBuilder(2 * last)

        fun extend(downs: Int, rights: Int) {
            if (downs == last && rights == last) {
                paths.add(moves.toString())
                return
            }
            // D is tried before R, so the paths come out in lexicographic order.
            if (downs < last) {
                moves.append('D')
                extend(downs + 1, rights)
                moves.deleteCharAt(moves.length - 1)
            }
            if (rights < last) {
                moves.append('R')
                extend(downs, rights + 1)
                moves.deleteCharAt(moves.length - 1)
            }
        }

        extend(0, 0)
        return paths
    }
}
