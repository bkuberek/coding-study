private const val STAY = -1
private const val SPILL = -2

/**
 * Water is kept as a depth per column, and a column's level is its height plus its water.
 *
 * One unit of water is one walk: try to the left, then to the right, one column at a time and
 * never uphill, and note where the final flat stretch of the walk begins. The walk either reaches
 * an edge (the unit falls off), ends lower than it began (the unit settles at the start of the
 * final flat stretch) or ends where it began (this direction does nothing).
 */
class Terrain(heights: List<Int>) {
    private val heights = heights.toIntArray()
    private val depths = IntArray(heights.size)
    private var spilledUnits = 0

    // Level 1
    fun render(): List<String> = picture(0, heights.size - 1)

    fun tallest(): Int = heights.maxOrNull() ?: 0

    // Level 2
    fun pour(column: Int): List<Int> {
        drop(column)
        return water()
    }

    fun water(): List<Int> = depths.toList()

    fun spilled(): Int = spilledUnits

    // Level 3
    fun pourMany(column: Int, units: Int): List<Int> {
        repeat(units) { drop(column) }
        return water()
    }

    // Level 4
    fun renderWindow(first: Int, last: Int): List<String> = picture(first, last)

    private fun level(column: Int): Int = heights[column] + depths[column]

    private fun drop(column: Int) {
        for (step in intArrayOf(-1, 1)) {
            val landing = walk(column, step)
            if (landing == SPILL) {
                spilledUnits++
                return
            }
            if (landing != STAY) {
                depths[landing]++
                return
            }
        }
        depths[column]++
    }

    private fun walk(column: Int, step: Int): Int {
        var at = column
        var flatStart = column
        while (true) {
            val ahead = at + step
            if (ahead < 0 || ahead >= heights.size) {
                return SPILL
            }
            if (level(ahead) > level(at)) {
                break
            }
            if (level(ahead) < level(at)) {
                flatStart = ahead
            }
            at = ahead
        }
        return if (level(flatStart) < level(column)) flatStart else STAY
    }

    private fun picture(first: Int, last: Int): List<String> {
        val top = heights.indices.maxOfOrNull { level(it) } ?: 0
        val rows = mutableListOf<String>()
        for (row in top downTo 1) {
            val cells = StringBuilder()
            for (column in first..last) {
                cells.append(
                    when {
                        heights[column] >= row -> '#'
                        level(column) >= row -> '~'
                        else -> '.'
                    },
                )
            }
            rows.add(cells.toString())
        }
        return rows
    }
}
