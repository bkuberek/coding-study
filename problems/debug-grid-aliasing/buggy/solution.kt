// Debug: Grid Aliasing. Some tests fail: find the bug and fix it.
class Solution {
    fun burnTimes(grid: Array<IntArray>): Array<IntArray> {
        val rows = grid.size
        val cols = grid[0].size
        val unburnt = IntArray(cols) { -1 }
        val times = Array(rows) { unburnt }
        for (r in 0 until rows) {
            for (c in 0 until cols) {
                if (grid[r][c] == 2) times[r][c] = 0
            }
        }

        var current = grid
        var minute = 0
        var spreading = true
        while (spreading) {
            minute++
            spreading = false
            val upcoming = current.copyOf()
            for (r in 0 until rows) {
                for (c in 0 until cols) {
                    if (current[r][c] != 2) continue
                    for ((dr, dc) in STEPS) {
                        val nr = r + dr
                        val nc = c + dc
                        if (nr in 0 until rows && nc in 0 until cols && current[nr][nc] == 1) {
                            upcoming[nr][nc] = 2
                            times[nr][nc] = minute
                            spreading = true
                        }
                    }
                }
            }
            current = upcoming
        }
        return times
    }

    private companion object {
        val STEPS = listOf(1 to 0, -1 to 0, 0 to 1, 0 to -1)
    }
}
