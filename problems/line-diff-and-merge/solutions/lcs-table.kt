private const val KEEP = ' '
private const val REMOVE = '-'
private const val ADD = '+'
private val HEADER = Regex("""^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@$""")
private val MARKERS = listOf("<<<<<<< ours", "||||||| base", "=======", ">>>>>>> theirs")

private data class Step(val kind: Char, val line: String)

private class Hunk(val start: Int) {
    val old = mutableListOf<String>()
    val fresh = mutableListOf<String>()
}

class LineDiff {
    private var last: List<String> = emptyList()

    // Level 1
    fun lcs(before: List<String>, after: List<String>): List<String> =
        script(before, after).filter { it.kind == KEEP }.map { it.line }

    fun diff(before: List<String>, after: List<String>): List<String> =
        script(before, after).map { "${it.kind}${it.line}" }

    // Level 2
    fun unified(before: List<String>, after: List<String>, context: Int): List<String> {
        val steps = script(before, after)
        val changed = steps.indices.filter { steps[it].kind != KEEP }
        if (changed.isEmpty()) return emptyList()
        val groups = mutableListOf<Pair<Int, Int>>()
        var first = changed[0]
        var previous = first
        for (index in changed.drop(1)) {
            if (index - previous - 1 > 2 * context) {
                groups.add(first to previous)
                first = index
            }
            previous = index
        }
        groups.add(first to previous)
        val lines = mutableListOf<String>()
        for ((groupFirst, groupLast) in groups) {
            val start = maxOf(0, groupFirst - context)
            val end = minOf(steps.size, groupLast + context + 1)
            val prior = steps.subList(0, start)
            val hunk = steps.subList(start, end)
            val oldRange = range(prior.count { it.kind != ADD }, hunk.count { it.kind != ADD })
            val newRange = range(prior.count { it.kind != REMOVE }, hunk.count { it.kind != REMOVE })
            lines.add("@@ -$oldRange +$newRange @@")
            hunk.mapTo(lines) { "${it.kind}${it.line}" }
        }
        return lines
    }

    // Level 3
    fun applyPatch(lines: List<String>, patch: List<String>, maxOffset: Int): List<String> {
        val result = lines.toMutableList()
        val statuses = mutableListOf<String>()
        var added = 0
        var shift = 0
        var floor = 0
        for (hunk in parseHunks(patch)) {
            val base = hunk.start + added
            val found = findHunk(result, hunk.old, base + shift, floor, maxOffset)
            if (found == null) {
                statuses.add("rejected")
                continue
            }
            val replaced = result.subList(found, found + hunk.old.size)
            replaced.clear()
            replaced.addAll(hunk.fresh)
            shift = found - base
            added += hunk.fresh.size - hunk.old.size
            floor = found + hunk.fresh.size
            statuses.add("applied $shift")
        }
        last = result
        return statuses
    }

    fun patched(): List<String> = last.toList()

    // Level 4
    fun merge(base: List<String>, ours: List<String>, theirs: List<String>): List<String> {
        val toOurs = keptAt(base, ours)
        val toTheirs = keptAt(base, theirs)
        val merged = mutableListOf<String>()
        var o = 0
        var a = 0
        var b = 0
        for ((index, line) in base.withIndex()) {
            val j = toOurs[index] ?: continue
            val k = toTheirs[index] ?: continue
            merged += resolve(base.subList(o, index), ours.subList(a, j), theirs.subList(b, k))
            merged += line
            o = index + 1
            a = j + 1
            b = k + 1
        }
        merged += resolve(base.subList(o, base.size), ours.subList(a, ours.size), theirs.subList(b, theirs.size))
        return merged
    }
}

/**
 * The diff with the most kept lines that, read from the top, keeps rather than removes and removes
 * rather than adds wherever both stay optimal.
 */
private fun script(before: List<String>, after: List<String>): List<Step> {
    val n = before.size
    val m = after.size
    // longest[i][j]: the length of a longest common subsequence of before[i:] and after[j:].
    val longest = Array(n + 1) { IntArray(m + 1) }
    for (i in n - 1 downTo 0) {
        for (j in m - 1 downTo 0) {
            longest[i][j] = if (before[i] == after[j]) {
                longest[i + 1][j + 1] + 1
            } else {
                maxOf(longest[i + 1][j], longest[i][j + 1])
            }
        }
    }
    val steps = mutableListOf<Step>()
    var i = 0
    var j = 0
    while (i < n || j < m) {
        if (i < n && j < m && before[i] == after[j]) {
            steps.add(Step(KEEP, before[i++]))
            j++
        } else if (i < n && (j == m || longest[i + 1][j] >= longest[i][j + 1])) {
            steps.add(Step(REMOVE, before[i++]))
        } else {
            steps.add(Step(ADD, after[j++]))
        }
    }
    return steps
}

private fun range(linesBefore: Int, size: Int): String = when (size) {
    0 -> "$linesBefore,0"
    1 -> "${linesBefore + 1}"
    else -> "${linesBefore + 1},$size"
}

/** Each hunk with the index where its old lines start, its old lines and its new lines. */
private fun parseHunks(patch: List<String>): List<Hunk> {
    val hunks = mutableListOf<Hunk>()
    for (line in patch) {
        val header = HEADER.matchEntire(line)
        if (header != null) {
            val oldStart = header.groupValues[1].toInt()
            val oldCount = header.groupValues[2].ifEmpty { "1" }.toInt()
            hunks.add(Hunk(if (oldCount > 0) oldStart - 1 else oldStart))
            continue
        }
        if (line.isEmpty()) continue
        val hunk = hunks.last()
        val text = line.substring(1)
        if (line[0] != ADD) hunk.old.add(text)
        if (line[0] != REMOVE) hunk.fresh.add(text)
    }
    return hunks
}

/** The nearest position to [expected] where [old] matches, the earlier one first. */
private fun findHunk(result: List<String>, old: List<String>, expected: Int, floor: Int, maxOffset: Int): Int? {
    for (distance in 0..maxOffset) {
        for (position in listOf(expected - distance, expected + distance)) {
            val fits = floor <= position && position + old.size <= result.size
            if (fits && result.subList(position, position + old.size) == old) return position
        }
    }
    return null
}

/** For each line of [base] that the diff to [other] keeps, the index it keeps it at. */
private fun keptAt(base: List<String>, other: List<String>): Map<Int, Int> {
    val kept = HashMap<Int, Int>()
    var i = 0
    var j = 0
    for (step in script(base, other)) {
        if (step.kind == KEEP) kept[i] = j
        if (step.kind != ADD) i++
        if (step.kind != REMOVE) j++
    }
    return kept
}

private fun resolve(base: List<String>, ours: List<String>, theirs: List<String>): List<String> = when {
    ours == theirs -> ours
    ours == base -> theirs
    theirs == base -> ours
    else -> listOf(MARKERS[0]) + ours + MARKERS[1] + base + MARKERS[2] + theirs + MARKERS[3]
}
