private const val GROUP_GAP_MS = 1000L
private const val ROOT = 0

/**
 * One recorded edit, kept as a command that can be applied and reverted: at [position], [removed]
 * was replaced by [inserted]. The step is also the history state it leads to.
 */
private class Step(val number: Int, val parent: Step?, val position: Int) {
    var removed = ""
    var inserted = ""
    val children = mutableListOf<Step>()
    var currentChild: Step? = null

    fun apply(text: String): String =
        text.substring(0, position) + inserted + text.substring(position + removed.length)

    fun revert(text: String): String =
        text.substring(0, position) + removed + text.substring(position + inserted.length)

    /** This step and every step above it, up to the root. */
    fun ancestors(): List<Step> = generateSequence(this) { it.parent }.toList()
}

class Editor(initial: String) {
    private var content = initial
    private val root = Step(ROOT, null, 0)
    private val steps = mutableListOf(root)
    private var current = root
    private val checkpoints = HashMap<String, String>()
    private var groupOpen = false
    private var lastTypedAt = 0L

    // Level 1
    fun insert(position: Int, text: String) {
        groupOpen = false
        record(minOf(position, content.length), "", text)
    }

    fun erase(position: Int, count: Int) {
        groupOpen = false
        val start = minOf(position, content.length)
        val end = minOf(content.length.toLong(), start.toLong() + count).toInt()
        record(start, content.substring(start, end), "")
    }

    fun undo(): Boolean {
        groupOpen = false
        val parent = current.parent ?: return false
        content = current.revert(content)
        current = parent
        return true
    }

    fun redo(): Boolean {
        groupOpen = false
        val child = current.currentChild ?: return false
        content = child.apply(content)
        current = child
        return true
    }

    fun text(): String = content

    // Level 2
    fun typeText(timestamp: Long, position: Int, text: String) {
        val at = minOf(position, content.length)
        if (joinsGroup(timestamp, at)) {
            content = content.substring(0, at) + text + content.substring(at)
            current.inserted += text
        } else {
            record(at, "", text)
        }
        groupOpen = true
        lastTypedAt = timestamp
    }

    private fun joinsGroup(timestamp: Long, position: Int): Boolean {
        val group = current
        return groupOpen &&
            position == group.position + group.inserted.length &&
            timestamp - lastTypedAt <= GROUP_GAP_MS &&
            !group.inserted.endsWith(" ")
    }

    // Level 3
    fun checkpoint(name: String) {
        groupOpen = false
        checkpoints[name] = content
    }

    fun restore(name: String): Boolean {
        groupOpen = false
        val saved = checkpoints[name] ?: return false
        record(0, content, saved)
        return true
    }

    // Level 4
    fun state(): Int = current.number

    fun branches(): List<Int> = current.children.map { it.number }

    fun jump(state: Int): Boolean {
        groupOpen = false
        if (state !in steps.indices) return false
        val target = steps[state]
        val pathDown = target.ancestors()
        val onTargetPath = pathDown.toHashSet()
        while (current !in onTargetPath) {
            content = current.revert(content)
            current = current.parent!!
        }
        val common = pathDown.indexOf(current)
        for (index in common - 1 downTo 0) {
            content = pathDown[index].apply(content)
        }
        for (index in 1 until pathDown.size) {
            pathDown[index].currentChild = pathDown[index - 1]
        }
        current = target
        return true
    }

    /** Records one step, unless it would leave the text as it is. */
    private fun record(position: Int, removed: String, inserted: String) {
        if (removed == inserted) return
        val step = Step(steps.size, current, position)
        step.removed = removed
        step.inserted = inserted
        steps.add(step)
        current.children.add(step)
        current.currentChild = step
        content = step.apply(content)
        current = step
    }
}
