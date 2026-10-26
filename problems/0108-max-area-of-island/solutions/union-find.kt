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

    /** Merges the groups of a and b and returns the size of the merged group. */
    fun union(a: Int, b: Int): Int {
        var rootA = find(a)
        var rootB = find(b)
        if (rootA != rootB) {
            if (size[rootA] < size[rootB]) rootA = rootB.also { rootB = rootA }
            parent[rootB] = rootA
            size[rootA] += size[rootB]
        }
        return size[rootA]
    }
}

class Solution {
    fun maxAreaOfIsland(grid: Array<IntArray>): Int {
        val rows = grid.size
        val cols = grid[0].size
        val sets = DisjointSet(rows * cols)
        var best = 0
        for (row in 0 until rows) {
            for (col in 0 until cols) {
                if (grid[row][col] != 1) continue
                val cell = row * cols + col
                best = maxOf(best, 1)
                if (col + 1 < cols && grid[row][col + 1] == 1) best = maxOf(best, sets.union(cell, cell + 1))
                if (row + 1 < rows && grid[row + 1][col] == 1) best = maxOf(best, sets.union(cell, cell + cols))
            }
        }
        return best
    }
}
