/**
 * Tasks describe the state a host should be in. Running a task compares that state with the host's
 * and changes the host only when they differ, so a second run finds nothing to do. A run works
 * through the hosts in batches; in each batch it applies every task to every host still standing,
 * then the handlers that a change notified. A check run does the same on copies of the hosts, so
 * later tasks see what earlier ones would have done while the real hosts stay as they were.
 */
class Converger {
    private class Host(
        val files: MutableMap<String, String> = HashMap(),
        val packages: MutableMap<String, String> = HashMap(),
        val facts: MutableMap<String, String> = HashMap(),
    ) {
        fun copy() = Host(HashMap(files), HashMap(packages), facts)
    }

    private data class Action(val kind: String, val target: String, val value: String)

    private val hosts = LinkedHashMap<String, Host>()
    private val tasks = LinkedHashMap<String, Action>()
    private val handlers = LinkedHashMap<String, Action>()
    private val links = HashMap<String, MutableList<String>>()
    private val conditions = HashMap<String, MutableList<Action>>()
    private var batch = 0
    private var counts: Map<String, Map<String, Int>> = emptyMap()

    // Level 1
    fun addHost(host: String): Boolean = hosts.putIfAbsent(host, Host()) == null

    fun setState(host: String, kind: String, target: String, value: String): Boolean {
        val found = hosts[host] ?: return false
        apply(found, kind, target, value)
        return true
    }

    fun addTask(name: String, kind: String, target: String, value: String): Boolean =
        tasks.putIfAbsent(name, Action(kind, target, value)) == null

    fun run(): List<List<String>> {
        val fresh = zeros()
        val rows = play(hosts, false, fresh)
        counts = fresh
        return rows
    }

    fun state(host: String): List<List<String>> {
        val found = hosts[host] ?: return emptyList()
        val rows = found.files.map { (path, content) -> listOf("file", path, content) } +
            found.packages.flatMap { (name, service) ->
                listOf(listOf("package", name, "present"), listOf("service", name, service))
            }
        return rows.sortedWith(compareBy({ it[0] }, { it[1] }))
    }

    // Level 2
    fun check(): List<List<String>> {
        val copies = LinkedHashMap<String, Host>()
        hosts.forEach { (name, host) -> copies[name] = host.copy() }
        return play(copies, true, zeros())
    }

    // Level 3
    fun addHandler(name: String, kind: String, target: String, value: String): Boolean =
        handlers.putIfAbsent(name, Action(kind, target, value)) == null

    fun notifies(task: String, handler: String): Boolean {
        if (task !in tasks || handler !in handlers) return false
        val linked = links.getOrPut(task) { mutableListOf() }
        if (handler in linked) return false
        linked.add(handler)
        return true
    }

    // Level 4
    fun setFact(host: String, key: String, value: String): Boolean {
        val found = hosts[host] ?: return false
        return found.facts.put(key, value) == null
    }

    fun onlyIf(task: String, fact: String, comparison: String, value: String): Boolean {
        if (task !in tasks) return false
        conditions.getOrPut(task) { mutableListOf() }.add(Action(fact, comparison, value))
        return true
    }

    fun setBatchSize(size: Int): Boolean {
        val changed = size != batch
        batch = size
        return changed
    }

    fun summary(): List<List<String>> = hosts.keys.map { host ->
        listOf(host) + COUNTED.map { (counts[host]?.get(it) ?: 0).toString() }
    }

    // Running
    private fun zeros(): MutableMap<String, MutableMap<String, Int>> =
        hosts.keys.associateWith { COUNTED.associateWith { 0 }.toMutableMap() }.toMutableMap()

    private fun play(
        on: Map<String, Host>,
        dry: Boolean,
        tally: MutableMap<String, MutableMap<String, Int>>,
    ): List<List<String>> {
        val names = on.keys.toList()
        val size = if (batch > 0) batch else maxOf(names.size, 1)
        val rows = mutableListOf<List<String>>()
        fun record(host: String, name: String, outcome: Pair<String, List<String>>) {
            val status = outcome.first
            tally.getValue(host)[status] = tally.getValue(host).getValue(status) + 1
            rows.add(listOf(host, name, status) + if (dry) outcome.second else emptyList())
        }
        for (group in names.chunked(size)) {
            val failed = HashSet<String>()
            val notified = group.associateWith { HashSet<String>() }
            for ((task, action) in tasks) {
                for (host in group) {
                    if (host in failed) continue
                    val outcome = task(on.getValue(host), task, action)
                    when (outcome.first) {
                        "failed" -> failed.add(host)
                        "changed" -> notified.getValue(host).addAll(links[task] ?: emptyList())
                    }
                    record(host, task, outcome)
                }
            }
            for ((handler, action) in handlers) {
                for (host in group) {
                    if (host in failed || handler !in notified.getValue(host)) continue
                    val outcome = change(on.getValue(host), action)
                    if (outcome.first == "failed") failed.add(host)
                    record(host, handler, outcome)
                }
            }
            if (failed.size == group.size) break
        }
        return rows
    }

    private fun task(host: Host, name: String, action: Action): Pair<String, List<String>> {
        for ((fact, operator, wanted) in conditions[name] ?: emptyList()) {
            val have = host.facts[fact] ?: return "failed" to emptyList()
            val holds = compare(have, operator, wanted) ?: return "failed" to emptyList()
            if (!holds) return "skipped" to emptyList()
        }
        return change(host, action)
    }

    private fun current(host: Host, kind: String, target: String): String? = when (kind) {
        "file" -> host.files[target] ?: ""
        "package" -> if (target in host.packages) "present" else "absent"
        else -> host.packages[target]
    }

    private fun change(host: Host, action: Action): Pair<String, List<String>> {
        val before = current(host, action.kind, action.target) ?: return "failed" to emptyList()
        if (before == action.value && action.value != "restarted") return "ok" to emptyList()
        apply(host, action.kind, action.target, action.value)
        return "changed" to listOf(before, action.value)
    }

    private fun apply(host: Host, kind: String, target: String, value: String) {
        when {
            kind == "file" -> host.files[target] = value
            kind == "package" && value == "present" -> host.packages.putIfAbsent(target, "stopped")
            kind == "package" -> host.packages.remove(target)
            else -> host.packages[target] = if (value == "restarted") "running" else value
        }
    }

    private companion object {
        val COUNTED = listOf("ok", "changed", "failed", "skipped")
        val WHOLE = Regex("-?[0-9]+")

        /** The truth of one condition, or null when it cannot be decided. */
        fun compare(fact: String, operator: String, value: String): Boolean? {
            if (operator == "==") return fact == value
            if (operator == "!=") return fact != value
            if (!WHOLE.matches(fact) || !WHOLE.matches(value)) return null
            val left = fact.toLong()
            val right = value.toLong()
            return when (operator) {
                "<" -> left < right
                "<=" -> left <= right
                ">" -> left > right
                else -> left >= right
            }
        }
    }
}
