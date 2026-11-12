import java.util.PriorityQueue

/**
 * Four classic sorts, each written the way the statement specifies it, with a meter that counts
 * the work of the latest sort. A sort returns a new array and never changes its input.
 */
class SortingWorkbench {
    private var meter = IntArray(0)
    private var mergeComparisons = 0

    // Level 1
    fun insertionSort(values: IntArray): IntArray {
        val items = values.copyOf()
        var comparisons = 0
        var moves = 0
        for (i in 1 until items.size) {
            val key = items[i]
            var j = i - 1
            while (j >= 0) {
                comparisons++
                if (items[j] <= key) break
                items[j + 1] = items[j]
                moves++
                j--
            }
            items[j + 1] = key
        }
        meter = intArrayOf(comparisons, moves)
        return items
    }

    fun report(): IntArray = meter.copyOf()

    // Level 2
    fun mergeSortBy(rows: Array<IntArray>, key: Int): Array<IntArray> {
        mergeComparisons = 0
        val merged = mergeSort(rows.toList(), key)
        meter = intArrayOf(mergeComparisons)
        return Array(merged.size) { merged[it].copyOf() }
    }

    private fun mergeSort(rows: List<IntArray>, key: Int): List<IntArray> {
        if (rows.size <= 1) return rows.toList()
        val middle = rows.size / 2
        val left = mergeSort(rows.subList(0, middle), key)
        val right = mergeSort(rows.subList(middle, rows.size), key)
        val merged = ArrayList<IntArray>(rows.size)
        var i = 0
        var j = 0
        while (i < left.size && j < right.size) {
            mergeComparisons++
            if (left[i][key] <= right[j][key]) merged.add(left[i++]) else merged.add(right[j++])
        }
        while (i < left.size) merged.add(left[i++])
        while (j < right.size) merged.add(right[j++])
        return merged
    }

    // Level 3
    fun quickSort(values: IntArray): IntArray {
        val items = values.copyOf()
        var calls = 0
        var steps = 0
        val ranges = ArrayDeque<IntArray>()
        ranges.addLast(intArrayOf(0, items.size - 1))
        while (ranges.isNotEmpty()) {
            val (low, high) = ranges.removeLast()
            if (high - low < 1) continue
            val (below, above) = partition(items, low, high)
            calls++
            steps += high - low + 1
            ranges.addLast(intArrayOf(low, below - 1))
            ranges.addLast(intArrayOf(above + 1, high))
        }
        meter = intArrayOf(calls, steps)
        return items
    }

    fun quickSelect(values: IntArray, k: Int): Int {
        val items = values.copyOf()
        val target = k - 1
        var calls = 0
        var steps = 0
        var low = 0
        var high = items.size - 1
        while (low < high) {
            val (below, above) = partition(items, low, high)
            calls++
            steps += high - low + 1
            if (target < below) {
                high = below - 1
            } else if (target > above) {
                low = above + 1
            } else {
                break
            }
        }
        meter = intArrayOf(calls, steps)
        return items[target]
    }

    /** Returns (below, above): items[low until below] < pivot, items[below..above] == pivot, the rest > pivot. */
    private fun partition(items: IntArray, low: Int, high: Int): Pair<Int, Int> {
        val pivot = items[low + (high - low) / 2]
        var below = low
        var i = low
        var above = high
        while (i <= above) {
            if (items[i] < pivot) {
                items[below] = items[i].also { items[i] = items[below] }
                below++
                i++
            } else if (items[i] > pivot) {
                items[i] = items[above].also { items[above] = items[i] }
                above--
            } else {
                i++
            }
        }
        return Pair(below, above)
    }

    // Level 4
    fun externalSort(values: IntArray, memory: Int, ways: Int): IntArray {
        var runs = values.toList().chunked(memory).map { it.sorted().toIntArray() }
        val initialRuns = runs.size
        var passes = 0
        while (runs.size > 1) {
            runs = runs.chunked(ways).map { mergeGroup(it) }
            passes++
        }
        meter = intArrayOf(initialRuns, passes)
        return if (runs.isEmpty()) IntArray(0) else runs[0]
    }

    /** A min-heap of (value, run, position in the run) holds the front value of each run. */
    private fun mergeGroup(group: List<IntArray>): IntArray {
        val heap = PriorityQueue<IntArray>(compareBy<IntArray>({ it[0] }, { it[1] }))
        group.forEachIndexed { index, run -> heap.add(intArrayOf(run[0], index, 0)) }
        val merged = IntArray(group.sumOf { it.size })
        var written = 0
        while (heap.isNotEmpty()) {
            val (value, index, position) = heap.poll()
            merged[written++] = value
            val run = group[index]
            if (position + 1 < run.size) heap.add(intArrayOf(run[position + 1], index, position + 1))
        }
        return merged
    }
}
