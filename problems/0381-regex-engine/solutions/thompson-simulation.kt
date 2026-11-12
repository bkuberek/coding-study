/**
 * A recursive-descent parser builds the syntax tree; Thompson's construction turns it into an
 * automaton with one state per character, class or operator; matching runs every live state in
 * step with the text, so it never backtracks. Compiled automata are cached by pattern.
 */
class RegexEngine {
    private val automata = HashMap<String, Automaton>()

    private fun automaton(pattern: String): Automaton =
        automata.getOrPut(pattern) { Automaton(Parser(pattern).parse()) }

    // Level 1
    fun parse(pattern: String): String =
        try {
            Parser(pattern).parse().show()
        } catch (error: PatternError) {
            "error: ${error.code} at ${error.position}"
        }

    // Level 2
    fun nfa(pattern: String): List<String> {
        val automaton = automaton(pattern)
        return (0 until automaton.size).map { automaton.line(it) }
    }

    // Level 3
    fun fullMatch(pattern: String, text: String): Boolean = automaton(pattern).run(text).first

    fun countSteps(pattern: String, text: String): Int = automaton(pattern).run(text).second

    // Level 4
    fun search(pattern: String, text: String): IntArray = automaton(pattern).leftmostLongest(text)

    class PatternError(val code: String, val position: Int) : RuntimeException(code)

    sealed class Node {
        data class Lit(val ch: Char) : Node()
        object AnyChar : Node()
        object Empty : Node()
        data class CharClass(val negated: Boolean, val items: List<Pair<Char, Char>>) : Node()
        data class Group(val kind: String, val parts: List<Node>) : Node()
        data class Repeat(val kind: String, val inner: Node) : Node()

        fun show(): String = when (this) {
            is Lit -> "'$ch'"
            AnyChar -> "any"
            Empty -> "empty"
            is CharClass -> showClass()
            is Group -> parts.joinToString(",", "$kind(", ")") { it.show() }
            is Repeat -> "$kind(${inner.show()})"
        }
    }

    companion object {
        private val REPEATS = mapOf('*' to "star", '+' to "plus", '?' to "opt")

        private fun Node.CharClass.showClass(): String =
            items.joinToString(",", if (negated) "notclass(" else "class(", ")") { (low, high) ->
                if (low == high) "'$low'" else "'$low'-'$high'"
            }

        private fun Node.CharClass.matches(c: Char): Boolean =
            items.any { (low, high) -> c in low..high } != negated
    }

    /** Recursive descent; a pattern has at most 100 characters, so the recursion stays shallow. */
    private class Parser(private val text: String) {
        private var pos = 0

        private fun peek(): Char? = if (pos < text.length) text[pos] else null

        fun parse(): Node {
            val node = alternation()
            if (pos < text.length) throw PatternError("unmatched-paren", pos)
            return node
        }

        private fun alternation(): Node {
            val branches = mutableListOf(sequence())
            while (peek() == '|') {
                pos++
                branches.add(sequence())
            }
            return if (branches.size == 1) branches[0] else Node.Group("alt", branches)
        }

        private fun sequence(): Node {
            val items = mutableListOf<Node>()
            while (peek() != null && peek() != '|' && peek() != ')') items.add(repetition())
            return when (items.size) {
                0 -> Node.Empty
                1 -> items[0]
                else -> Node.Group("cat", items)
            }
        }

        private fun repetition(): Node {
            if (peek() in REPEATS) throw PatternError("nothing-to-repeat", pos)
            var node = atom()
            while (peek() in REPEATS) {
                node = Node.Repeat(REPEATS.getValue(peek()!!), node)
                pos++
            }
            return node
        }

        private fun atom(): Node {
            val start = pos
            val c = text[pos++]
            return when (c) {
                '(' -> {
                    val inner = alternation()
                    if (peek() != ')') throw PatternError("unclosed-group", start)
                    pos++
                    inner
                }
                '.' -> Node.AnyChar
                '[' -> charClass(start)
                else -> Node.Lit(c)
            }
        }

        private fun charClass(start: Int): Node {
            val negated = peek() == '^'
            if (negated) pos++
            val items = mutableListOf<Pair<Char, Char>>()
            while (true) {
                if (pos >= text.length) throw PatternError("unclosed-class", start)
                if (peek() == ']') {
                    if (items.isEmpty()) throw PatternError("empty-class", start)
                    pos++
                    return Node.CharClass(negated, items)
                }
                val lowAt = pos
                val low = text[pos++]
                val isRange = peek() == '-' && pos + 1 < text.length && text[pos + 1] != ']'
                if (isRange) {
                    val high = text[pos + 1]
                    if (high < low) throw PatternError("bad-range", lowAt)
                    pos += 2
                    items.add(low to high)
                } else {
                    items.add(low to low)
                }
            }
        }
    }

    /** Parallel lists: the kind of each state, the node labelling a char or class state, its arrows. */
    class Automaton(root: Node) {
        private var kind = mutableListOf<String>()
        private var label = mutableListOf<Node?>()
        private var outs = mutableListOf<IntArray>()
        private var finalState = 0
        val size: Int get() = kind.size

        init {
            val (start, holes) = fragment(root)
            patch(holes, add("match", null, 0))
            renumber(start)
        }

        private fun add(k: String, node: Node?, arrows: Int): Int {
            kind.add(k)
            label.add(node)
            outs.add(IntArray(arrows) { -1 })
            return kind.size - 1
        }

        private fun patch(holes: List<Pair<Int, Int>>, target: Int) {
            for ((state, index) in holes) outs[state][index] = target
        }

        private fun fragment(node: Node): Pair<Int, List<Pair<Int, Int>>> = when (node) {
            is Node.Lit, Node.AnyChar, Node.Empty, is Node.CharClass -> {
                val k = when (node) {
                    is Node.Lit -> "char"
                    Node.AnyChar -> "any"
                    Node.Empty -> "empty"
                    else -> "class"
                }
                val state = add(k, node, 1)
                state to listOf(state to 0)
            }
            is Node.Group -> if (node.kind == "cat") {
                val (first, firstHoles) = fragment(node.parts[0])
                var holes = firstHoles
                for (part in node.parts.drop(1)) {
                    val (next, nextHoles) = fragment(part)
                    patch(holes, next)
                    holes = nextHoles
                }
                first to holes
            } else {
                val split = add("split", null, node.parts.size)
                val holes = mutableListOf<Pair<Int, Int>>()
                node.parts.forEachIndexed { index, part ->
                    val (side, sideHoles) = fragment(part)
                    outs[split][index] = side
                    holes.addAll(sideHoles)
                }
                split to holes
            }
            is Node.Repeat -> {
                val (inner, innerHoles) = fragment(node.inner)
                val split = add("split", null, 2)
                outs[split][0] = inner
                when (node.kind) {
                    "star" -> {
                        patch(innerHoles, split)
                        split to listOf(split to 1)
                    }
                    "plus" -> {
                        patch(innerHoles, split)
                        inner to listOf(split to 1)
                    }
                    else -> split to innerHoles + (split to 1)
                }
            }
        }

        /** Breadth first from the start state: the start is 0, and each arrow's unseen target is next. */
        private fun renumber(start: Int) {
            val number = IntArray(kind.size) { -1 }
            val order = mutableListOf(start)
            number[start] = 0
            var i = 0
            while (i < order.size) {
                for (target in outs[order[i]]) {
                    if (number[target] < 0) {
                        number[target] = order.size
                        order.add(target)
                    }
                }
                i++
            }
            kind = order.map { kind[it] }.toMutableList()
            label = order.map { label[it] }.toMutableList()
            outs = order.map { state -> IntArray(outs[state].size) { number[outs[state][it]] } }.toMutableList()
            finalState = kind.indexOf("match")
        }

        fun line(state: Int): String {
            val node = label[state]
            val head = when (kind[state]) {
                "char" -> "char '${(node as Node.Lit).ch}'"
                "class" -> (node as Node.CharClass).showClass()
                else -> kind[state]
            }
            val arrows = outs[state]
            return if (arrows.isEmpty()) "$state: $head" else "$state: $head -> ${arrows.joinToString(", ")}"
        }

        private fun accepts(state: Int, c: Char): Boolean = when (kind[state]) {
            "char" -> (label[state] as Node.Lit).ch == c
            "any" -> true
            "class" -> (label[state] as Node.CharClass).matches(c)
            else -> false
        }

        /** Every state reachable from the sources through split and empty arrows, sources included. */
        private fun closure(sources: List<Int>): List<Int> {
            val seen = BooleanArray(kind.size)
            val reached = mutableListOf<Int>()
            val stack = ArrayDeque(sources.reversed())
            while (stack.isNotEmpty()) {
                val state = stack.removeLast()
                if (seen[state]) continue
                seen[state] = true
                reached.add(state)
                if (kind[state] == "split" || kind[state] == "empty") {
                    for (target in outs[state].reversed()) stack.addLast(target)
                }
            }
            return reached
        }

        private fun advance(current: List<Int>, c: Char): List<Int> =
            closure(current.filter { accepts(it, c) }.map { outs[it][0] })

        fun run(text: String): Pair<Boolean, Int> {
            var current = closure(listOf(0))
            var steps = current.size
            for (c in text) {
                current = advance(current, c)
                steps += current.size
                if (current.isEmpty()) return false to steps
            }
            return (finalState in current) to steps
        }

        /**
         * One pass: each live state carries the earliest start that reaches it, and the live list
         * stays ordered by start. After a match, later starts are dropped and the scan goes on while
         * a state with that start or an earlier one is alive.
         */
        fun leftmostLongest(text: String): IntArray {
            var best: IntArray? = null
            var live = mutableListOf<IntArray>()
            for (position in 0..text.length) {
                if (best == null) {
                    val have = live.map { it[0] }.toSet()
                    for (state in closure(listOf(0))) {
                        if (state !in have) live.add(intArrayOf(state, position))
                    }
                }
                for ((state, start) in live) {
                    val current = best
                    if (state == finalState && (current == null || start <= current[0])) {
                        best = intArrayOf(start, position)
                    }
                }
                val found = best
                if (found != null) live = live.filter { it[1] <= found[0] }.toMutableList()
                if (position == text.length || live.isEmpty()) break
                val seen = BooleanArray(kind.size)
                val moved = mutableListOf<IntArray>()
                for ((state, start) in live) {
                    if (!accepts(state, text[position])) continue
                    for (reached in closure(listOf(outs[state][0]))) {
                        if (!seen[reached]) {
                            seen[reached] = true
                            moved.add(intArrayOf(reached, start))
                        }
                    }
                }
                live = moved
            }
            return best ?: intArrayOf(-1, -1)
        }
    }
}
