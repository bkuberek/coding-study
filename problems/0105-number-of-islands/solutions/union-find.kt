private class DisjointSet(count: Int) {
    private val parent = IntArray(count) { it }
    private val size = IntArray(count) { 1 }

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

    fun union(a: Int, b: Int): Boolean {
        var rootA = find(a)
        var rootB = find(b)
        if (rootA == rootB) return false
        if (size[rootA] < size[rootB]) rootA = rootB.also { rootB = rootA }
        parent[rootB] = rootA
        size[rootA] += size[rootB]
        return true
    }
}

class Solution {
    fun numIslands(grid: Array<CharArray>): Int {
        val rows = grid.size
        val cols = grid[0].size
        val sets = DisjointSet(rows * cols)
        var islands = 0
        for (row in 0 until rows) {
            for (col in 0 until cols) {
                if (grid[row][col] != '1') continue
                islands++
                val cell = row * cols + col
                if (col + 1 < cols && grid[row][col + 1] == '1' && sets.union(cell, cell + 1)) islands--
                if (row + 1 < rows && grid[row + 1][col] == '1' && sets.union(cell, cell + cols)) islands--
            }
        }
        return islands
    }
}
