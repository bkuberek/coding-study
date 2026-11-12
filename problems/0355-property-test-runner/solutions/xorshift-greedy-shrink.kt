/**
 * Generators are prefix token lists parsed into a small tree. One xorshift32 stream feeds a whole
 * call, so every value is fixed by the seed and its position. Shrinking is greedy: from the
 * failing value, take the first candidate that still fails, and start again from it, until no
 * candidate fails. Candidates are built from the generator, so each one is a value the generator
 * could have drawn: in range, long enough and through every filter. The stateful level runs each
 * command sequence on the correct queue and on the buggy one and shrinks the sequence the same
 * way, keeping only sequences whose commands are all allowed.
 */
class PropertyRunner {
    private sealed class Gen {
        class IntGen(val low: Int, val high: Int) : Gen()
        class ListGen(val min: Int, val max: Int, val element: Gen) : Gen()
        class PairGen(val first: Gen, val second: Gen) : Gen()
        class FilterGen(val name: String, val inner: Gen) : Gen()
    }

    private sealed class Value {
        data class IntValue(val value: Int) : Value()
        data class ListValue(val items: List<Value>) : Value()
        data class PairValue(val first: Value, val second: Value) : Value()
    }

    private class GiveUp : RuntimeException()

    private class RandomStream(seed: Int, private val limit: Int) {
        private var state = seed
        private var discards = 0

        fun next(): Long {
            var x = state
            x = x xor (x shl 13)
            x = x xor (x ushr 17)
            x = x xor (x shl 5)
            state = x
            return x.toLong() and 0xFFFFFFFFL
        }

        fun between(low: Int, high: Int): Int = (low + next() % (high.toLong() - low + 1)).toInt()

        fun discard() {
            discards++
            if (discards > limit) throw GiveUp()
        }
    }

    private class BoundedQueue(private val capacity: Int, private val bug: String) {
        val items = ArrayDeque<Int>()
        private var puts = 0

        fun allows(command: String): Boolean = command != "get" || items.isNotEmpty()

        fun apply(command: String): String {
            if (command == "size") {
                return (if (bug == "size-wraps") items.size % capacity else items.size).toString()
            }
            if (command == "get") {
                if (items.isEmpty()) return "empty"
                if (bug == "wrap-lifo" && puts > capacity) return items.removeLast().toString()
                return items.removeFirst().toString()
            }
            val value = command.substring(4).toInt()
            if (items.size == capacity) {
                if (bug != "full-overwrites") return "full"
                items.removeFirst()
            } else if (bug == "repeat-dropped" && items.isNotEmpty() && items.last() == value) {
                puts++
                return "ok"
            }
            items.addLast(value)
            puts++
            return "ok"
        }
    }

    private var limit = 100

    // Level 1
    fun randoms(seed: Int, count: Int): List<Long> {
        val rng = RandomStream(seed, limit)
        return List(count) { rng.next() }
    }

    fun generate(gen: String, seed: Int, count: Int): List<String> {
        val rng = RandomStream(seed, limit)
        val parsed = generator(gen)
        val values = ArrayList<String>()
        try {
            repeat(count) { values.add(text(draw(parsed, rng))) }
        } catch (stop: GiveUp) {
            // the values completed before the limit are the answer
        }
        return values
    }

    fun check(gen: String, prop: String, seed: Int, runs: Int): String {
        val (kind, run, value) = search(gen, prop, seed, runs)
        return when (kind) {
            "failed" -> "failed $run: ${text(value!!)}"
            "gave up" -> "gave up after $run"
            else -> "passed $runs"
        }
    }

    // Level 2
    fun candidates(gen: String, seed: Int, index: Int): List<String> {
        val rng = RandomStream(seed, limit)
        val parsed = generator(gen)
        var value: Value = Value.IntValue(0)
        try {
            repeat(index) { value = draw(parsed, rng) }
        } catch (stop: GiveUp) {
            return emptyList()
        }
        return candidatesOf(parsed, value).map { text(it) }
    }

    fun minimize(gen: String, prop: String, seed: Int, runs: Int): List<String> {
        val (kind, _, found) = search(gen, prop, seed, runs)
        if (kind != "failed") return emptyList()
        val parsed = generator(gen)
        var value = found!!
        val path = mutableListOf(text(value))
        while (true) {
            value = candidatesOf(parsed, value).firstOrNull { !holds(prop, it) } ?: return path
            path.add(text(value))
        }
    }

    // Level 3
    fun setDiscardLimit(limit: Int) {
        this.limit = limit
    }

    // Level 4
    fun replay(capacity: Int, bug: String, commands: List<String>): List<String> {
        val model = BoundedQueue(capacity, "none")
        val system = BoundedQueue(capacity, bug)
        val answers = ArrayList<String>()
        for (command in commands) {
            if (!model.allows(command)) {
                answers.add("invalid")
                break
            }
            model.apply(command)
            answers.add(system.apply(command))
        }
        return answers
    }

    fun generateCommands(capacity: Int, seed: Int, count: Int, maxLength: Int): List<String> {
        val rng = RandomStream(seed, limit)
        return List(count) { sequence(capacity, rng, maxLength).joinToString(", ") }
    }

    fun firstFailure(capacity: Int, bug: String, seed: Int, runs: Int, maxLength: Int): List<String> {
        val rng = RandomStream(seed, limit)
        repeat(runs) {
            val commands = sequence(capacity, rng, maxLength)
            if (fails(capacity, bug, commands)) return commands
        }
        return emptyList()
    }

    fun shrinkFailure(capacity: Int, bug: String, seed: Int, runs: Int, maxLength: Int): List<String> {
        var commands = firstFailure(capacity, bug, seed, runs, maxLength)
        while (commands.isNotEmpty()) {
            commands = sequenceCandidates(capacity, commands).firstOrNull { fails(capacity, bug, it) } ?: break
        }
        return commands
    }

    private data class Outcome(val kind: String, val run: Int, val value: Value?)

    private fun search(gen: String, prop: String, seed: Int, runs: Int): Outcome {
        val rng = RandomStream(seed, limit)
        val parsed = generator(gen)
        var passed = 0
        try {
            for (run in 1..runs) {
                val value = draw(parsed, rng)
                if (!holds(prop, value)) return Outcome("failed", run, value)
                passed++
            }
        } catch (stop: GiveUp) {
            return Outcome("gave up", passed, null)
        }
        return Outcome("passed", runs, null)
    }

    private companion object {
        fun parse(tokens: List<String>, at: Int): Pair<Gen, Int> = when (tokens[at]) {
            "int" -> Gen.IntGen(tokens[at + 1].toInt(), tokens[at + 2].toInt()) to at + 3
            "list" -> {
                val (element, end) = parse(tokens, at + 3)
                Gen.ListGen(tokens[at + 1].toInt(), tokens[at + 2].toInt(), element) to end
            }
            "pair" -> {
                val (first, middle) = parse(tokens, at + 1)
                val (second, end) = parse(tokens, middle)
                Gen.PairGen(first, second) to end
            }
            else -> {
                val (inner, end) = parse(tokens, at + 2)
                Gen.FilterGen(tokens[at + 1], inner) to end
            }
        }

        fun generator(text: String): Gen = parse(text.split(" "), 0).first

        fun draw(gen: Gen, rng: RandomStream): Value = when (gen) {
            is Gen.IntGen -> Value.IntValue(rng.between(gen.low, gen.high))
            is Gen.ListGen -> {
                val length = rng.between(gen.min, gen.max)
                Value.ListValue(List(length) { draw(gen.element, rng) })
            }
            is Gen.PairGen -> {
                val first = draw(gen.first, rng)
                Value.PairValue(first, draw(gen.second, rng))
            }
            is Gen.FilterGen -> {
                var value = draw(gen.inner, rng)
                while (!passesFilter(gen.name, value)) {
                    rng.discard()
                    value = draw(gen.inner, rng)
                }
                value
            }
        }

        fun text(value: Value): String = when (value) {
            is Value.IntValue -> value.value.toString()
            is Value.ListValue -> value.items.joinToString(",", "[", "]") { text(it) }
            is Value.PairValue -> "(${text(value.first)},${text(value.second)})"
        }

        fun number(value: Value): Int = (value as Value.IntValue).value

        fun items(value: Value): List<Value> = (value as Value.ListValue).items

        fun numbers(value: Value): MutableList<Int> = items(value).map { number(it) }.toMutableList()

        fun passesFilter(name: String, value: Value): Boolean = when (name) {
            "even" -> number(value) % 2 == 0
            "odd" -> number(value) % 2 != 0
            "nonzero" -> number(value) != 0
            "positive" -> number(value) > 0
            "nonempty" -> items(value).isNotEmpty()
            "distinct" -> items(value).map { text(it) }.toSet().size == items(value).size
            else -> {
                val pair = value as Value.PairValue
                text(pair.first) != text(pair.second)
            }
        }

        fun total(value: Value): Int = when (value) {
            is Value.IntValue -> value.value
            is Value.ListValue -> value.items.sumOf { total(it) }
            is Value.PairValue -> total(value.first) + total(value.second)
        }

        fun ordered(values: List<Int>): Boolean = values.zipWithNext().all { (a, b) -> a <= b }

        fun holds(prop: String, value: Value): Boolean {
            val parts = prop.split(" ")
            val k = if (parts.size > 1) parts[1].toInt() else 0
            return when (parts[0]) {
                "lt" -> number(value) < k
                "not-multiple" -> number(value) % k != 0
                "sum-lt" -> total(value) < k
                "len-lt" -> items(value).size < k
                "ordered" -> ordered(numbers(value))
                "sort-ordered" -> ordered(numbers(value).sorted())
                "one-pass-ordered" -> {
                    val list = numbers(value)
                    for (i in 0 until list.size - 1) {
                        if (list[i] > list[i + 1]) list[i] = list[i + 1].also { list[i + 1] = list[i] }
                    }
                    ordered(list)
                }
                "max-from-zero" -> {
                    val list = numbers(value)
                    list.isEmpty() || list.fold(0) { best, item -> maxOf(best, item) } == list.max()
                }
                "keys-distinct" -> {
                    val pairs = items(value).map { it as Value.PairValue }
                    pairs.map { text(it.first) }.toSet().size == pairs.size
                }
                else -> {
                    val first = HashMap<String, String>()
                    val last = HashMap<String, String>()
                    for (item in items(value)) {
                        val pair = item as Value.PairValue
                        first.putIfAbsent(text(pair.first), text(pair.second))
                        last[text(pair.first)] = text(pair.second)
                    }
                    first == last
                }
            }
        }

        fun intCandidates(low: Int, high: Int, value: Int): List<Int> {
            val target = if (low > 0) low else if (high < 0) high else 0
            if (value == target) return emptyList()
            val found = mutableListOf(target)
            var step = (value - target) / 2
            while (step != 0) {
                found.add(value - step)
                step /= 2
            }
            return found
        }

        fun <T> withoutRepeats(value: T, found: List<T>, show: (T) -> String): List<T> {
            val seen = hashSetOf(show(value))
            return found.filter { seen.add(show(it)) }
        }

        fun <T> removals(items: List<T>, shortest: Int): MutableList<List<T>> {
            val n = items.size
            val found = mutableListOf<List<T>>()
            var size = n
            while (size >= 1) {
                if (n - size >= shortest) {
                    var start = 0
                    while (start + size <= n) {
                        found.add(items.subList(0, start) + items.subList(start + size, n))
                        start += size
                    }
                }
                size /= 2
            }
            return found
        }

        fun <T> replaced(items: List<T>, index: Int, item: T): List<T> =
            items.toMutableList().also { it[index] = item }

        fun candidatesOf(gen: Gen, value: Value): List<Value> {
            val found: List<Value> = when (gen) {
                is Gen.IntGen -> intCandidates(gen.low, gen.high, number(value)).map { Value.IntValue(it) }
                is Gen.ListGen -> {
                    val list = items(value)
                    val shorter = removals(list, gen.min).map { Value.ListValue(it) }
                    val simpler = list.indices.flatMap { i ->
                        candidatesOf(gen.element, list[i]).map { Value.ListValue(replaced(list, i, it)) }
                    }
                    shorter + simpler
                }
                is Gen.PairGen -> {
                    val pair = value as Value.PairValue
                    candidatesOf(gen.first, pair.first).map { Value.PairValue(it, pair.second) } +
                        candidatesOf(gen.second, pair.second).map { Value.PairValue(pair.first, it) }
                }
                is Gen.FilterGen -> candidatesOf(gen.inner, value).filter { passesFilter(gen.name, it) }
            }
            return withoutRepeats(value, found) { text(it) }
        }

        fun valid(capacity: Int, commands: List<String>): Boolean {
            val model = BoundedQueue(capacity, "none")
            for (command in commands) {
                if (!model.allows(command)) return false
                model.apply(command)
            }
            return true
        }

        fun fails(capacity: Int, bug: String, commands: List<String>): Boolean {
            val model = BoundedQueue(capacity, "none")
            val system = BoundedQueue(capacity, bug)
            return commands.any { model.apply(it) != system.apply(it) }
        }

        fun sequence(capacity: Int, rng: RandomStream, longest: Int): List<String> {
            val model = BoundedQueue(capacity, "none")
            return List(rng.between(1, longest)) {
                val allowed = if (model.items.isEmpty()) listOf("put", "size") else listOf("put", "get", "size")
                var command = allowed[(rng.next() % allowed.size).toInt()]
                if (command == "put") command = "put ${rng.between(0, 9)}"
                model.apply(command)
                command
            }
        }

        fun sequenceCandidates(capacity: Int, commands: List<String>): List<List<String>> {
            val found = removals(commands, 1)
            commands.forEachIndexed { i, command ->
                if (command.startsWith("put ")) {
                    for (smaller in intCandidates(0, 9, command.substring(4).toInt())) {
                        found.add(replaced(commands, i, "put $smaller"))
                    }
                }
            }
            return withoutRepeats(commands, found) { it.joinToString(", ") }.filter { valid(capacity, it) }
        }
    }
}
