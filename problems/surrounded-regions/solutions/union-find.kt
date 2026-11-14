private class DisjointSet(count: Int) {
    private val parent = IntArray(count) { it }
    private val rank = ByteArray(count)

    fun find(start: Int): Int {
        var root = start
        while (parent[root] != root) root = parent[root]
        var cell = start
        while (parent[cell] != root) {
            val next = parent[cell]
            parent[cell] = root
            cell = next
        }
        return root
    }

    fun union(a: Int, b: Int) {
        var rootA = find(a)
        var rootB = find(b)
        if (rootA == rootB) return
        if (rank[rootA] < rank[rootB]) rootA = rootB.also { rootB = rootA }
        parent[rootB] = rootA
        if (rank[rootA] == rank[rootB]) rank[rootA]++
    }
}

class Solution {
    fun solve(board: Array<CharArray>) {
        val rows = board.size
        val cols = board[0].size
        val edge = rows * cols // a virtual node that every 'O' on the edge joins
        val sets = DisjointSet(rows * cols + 1)
        for (r in 0 until rows) {
            for (c in 0 until cols) {
                if (board[r][c] != 'O') continue
                val cell = r * cols + c
                if (r == 0 || r == rows - 1 || c == 0 || c == cols - 1) sets.union(cell, edge)
                if (c + 1 < cols && board[r][c + 1] == 'O') sets.union(cell, cell + 1)
                if (r + 1 < rows && board[r + 1][c] == 'O') sets.union(cell, cell + cols)
            }
        }
        val edgeRoot = sets.find(edge)
        for (r in 0 until rows) {
            for (c in 0 until cols) {
                if (board[r][c] == 'O' && sets.find(r * cols + c) != edgeRoot) board[r][c] = 'X'
            }
        }
    }
}
